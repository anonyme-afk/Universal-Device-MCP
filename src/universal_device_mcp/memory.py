"""Persistent per-device knowledge store backed by SQLite."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .models import Device, utc_now


def _default_database_path() -> Path:
    """Resolve the conventional per-user data directory without a hard dependency."""
    import sys
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "UniversalDeviceMCP" / "devices.sqlite3"


_VOLATILE_CONFIGURATION_KEYS = {
    "address", "rssi", "signal_strength", "service_data", "manufacturer_data",
    "advertisement_data", "last_seen", "timestamp", "adb_state",
}


def _stable_configuration(value: Any) -> Any:
    """Drop runtime-only observations before comparing physical configuration."""
    if isinstance(value, dict):
        result = {key: _stable_configuration(item) for key, item in value.items()
                  if key.lower() not in _VOLATILE_CONFIGURATION_KEYS}
        if result.get("transport") == "adb":
            # ADB's shell interface appears only after the user authorizes debugging;
            # that is an access-state change, not a hardware-layout change.
            if isinstance(result.get("identity"), dict):
                result["identity"].pop("state", None)
            result["interfaces"] = [{"id": "shell", "kind": "adb-shell"}]
        elif result.get("transport") == "ios":
            # Lockdown access and service visibility change when the owner unlocks
            # and trusts the host; they are not physical hardware reconfigurations.
            identity = result.get("identity")
            if isinstance(identity, dict):
                identifier = identity.get("udid") or identity.get("serial")
                result["identity"] = {"identifier": identifier} if identifier else {}
            result["interfaces"] = []
        return result
    if isinstance(value, list):
        return [_stable_configuration(item) for item in value]
    return value


class DeviceMemory:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else _default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self.purge_history(int(os.environ.get("UDMCP_RETENTION_DAYS", "30")))

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _initialize(self) -> None:
        with self._connect() as con:
            con.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL UNIQUE,
                    transport TEXT NOT NULL, name TEXT NOT NULL, identity_json TEXT NOT NULL,
                    hardware_json TEXT NOT NULL, interfaces_json TEXT NOT NULL,
                    first_seen TEXT NOT NULL, last_seen TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS discoveries (
                    discovery_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
                    category TEXT NOT NULL, content_json TEXT NOT NULL,
                    confidence TEXT NOT NULL CHECK(confidence IN ('hypothesis','confirmed')),
                    source TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
                    interface_id TEXT, operation TEXT NOT NULL, request_json TEXT NOT NULL,
                    response_json TEXT, success INTEGER NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS device_snapshots (
                    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
                    snapshot_json TEXT NOT NULL, observed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS device_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS device_groups (
                    group_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
                    selector_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_discoveries_device ON discoveries(device_id);
                CREATE INDEX IF NOT EXISTS idx_experiments_device ON experiments(device_id);
                CREATE INDEX IF NOT EXISTS idx_snapshots_device ON device_snapshots(device_id);
                CREATE INDEX IF NOT EXISTS idx_events_device ON device_events(device_id);
            """)

    def save_device(self, device: Device) -> dict[str, Any]:
        now = utc_now()
        configuration = _stable_configuration({"transport": device.transport,
                                                "identity": device.identity, "hardware": device.hardware,
                                                "interfaces": device.interfaces})
        with self._connect() as con:
            existing = con.execute("SELECT * FROM devices WHERE fingerprint=?", (device.fingerprint,)).fetchone()
            device_id = existing["device_id"] if existing else device.device_id
            configuration_changed = False
            if existing:
                previous_configuration = _stable_configuration({
                    "transport": existing["transport"],
                    "identity": json.loads(existing["identity_json"]),
                    "hardware": json.loads(existing["hardware_json"]),
                    "interfaces": json.loads(existing["interfaces_json"]),
                })
                configuration_changed = previous_configuration != configuration
            con.execute("""INSERT INTO devices VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(fingerprint) DO UPDATE SET transport=excluded.transport,
                name=excluded.name, identity_json=excluded.identity_json,
                hardware_json=excluded.hardware_json, interfaces_json=excluded.interfaces_json,
                last_seen=excluded.last_seen""",
                (device_id, device.fingerprint, device.transport, device.name,
                 json.dumps(device.identity, default=str), json.dumps(device.hardware, default=str),
                 json.dumps(device.interfaces, default=str), existing["first_seen"] if existing else now, now))
            if not existing or configuration_changed:
                con.execute("INSERT INTO device_snapshots(device_id,snapshot_json,observed_at) VALUES(?,?,?)",
                            (device_id, json.dumps(configuration, default=str), now))
        result = self.get_device(device_id) or {}
        result["configuration_changed"] = configuration_changed
        return result

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM devices WHERE device_id=? OR fingerprint=?", (device_id, device_id)).fetchone()
            return self._device_row(row) if row else None

    def find_by_fingerprint(self, fingerprint: str) -> dict[str, Any] | None:
        return self.get_device(fingerprint)

    def update_device(self, device_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        allowed = {"name", "identity", "hardware", "interfaces"}
        unknown = set(updates) - allowed
        if unknown:
            raise ValueError(f"Unsupported profile fields: {', '.join(sorted(unknown))}")
        if not updates:
            raise ValueError("At least one profile field must be provided")
        with self._connect() as con:
            row = con.execute("SELECT * FROM devices WHERE device_id=? OR fingerprint=?", (device_id, device_id)).fetchone()
            if not row:
                raise KeyError(f"Unknown device: {device_id}")
            values: dict[str, Any] = {}
            for key in ("identity", "hardware", "interfaces"):
                if key in updates:
                    if key == "interfaces":
                        if not isinstance(updates[key], list):
                            raise ValueError("interfaces must be a list")
                        values[key] = updates[key]
                    else:
                        if not isinstance(updates[key], dict):
                            raise ValueError(f"{key} must be an object")
                        values[key] = {**json.loads(row[f"{key}_json"]), **updates[key]}
            if "name" in updates:
                if not isinstance(updates["name"], str) or not updates["name"].strip():
                    raise ValueError("name must be a non-empty string")
                values["name"] = updates["name"]
            identity = values.get("identity", json.loads(row["identity_json"]))
            hardware = values.get("hardware", json.loads(row["hardware_json"]))
            interfaces = values.get("interfaces", json.loads(row["interfaces_json"]))
            previous_configuration = _stable_configuration({
                "transport": row["transport"],
                "identity": json.loads(row["identity_json"]),
                "hardware": json.loads(row["hardware_json"]),
                "interfaces": json.loads(row["interfaces_json"]),
            })
            configuration = _stable_configuration({"transport": row["transport"],
                                                    "identity": identity, "hardware": hardware,
                                                    "interfaces": interfaces})
            configuration_changed = configuration != previous_configuration
            con.execute("UPDATE devices SET name=?,identity_json=?,hardware_json=?,interfaces_json=? WHERE device_id=?",
                        (values.get("name", row["name"]), json.dumps(identity, default=str),
                         json.dumps(hardware, default=str), json.dumps(interfaces, default=str), row["device_id"]))
            if configuration_changed:
                con.execute("INSERT INTO device_snapshots(device_id,snapshot_json,observed_at) VALUES(?,?,?)",
                            (row["device_id"], json.dumps(configuration, default=str), utc_now()))
            con.execute("INSERT INTO device_events(device_id,event_type,details_json,created_at) VALUES(?,?,?,?)",
                        (row["device_id"], "profile_updated", json.dumps({"fields": sorted(updates)}, default=str), utc_now()))
        result = self.get_device(row["device_id"]) or {}
        result["configuration_changed"] = configuration_changed
        return result

    def delete_device(self, device_id: str) -> str | None:
        with self._connect() as con:
            row = con.execute("SELECT device_id FROM devices WHERE device_id=? OR fingerprint=?", (device_id, device_id)).fetchone()
            if not row:
                return None
            canonical_id = row["device_id"]
            con.execute("DELETE FROM devices WHERE device_id=?", (canonical_id,))
            return canonical_id

    def list_devices(self) -> list[dict[str, Any]]:
        with self._connect() as con:
            return [self._device_row(r) for r in con.execute("SELECT * FROM devices ORDER BY last_seen DESC")]

    @staticmethod
    def _device_row(row: sqlite3.Row) -> dict[str, Any]:
        return {"device_id": row["device_id"], "fingerprint": row["fingerprint"],
                "transport": row["transport"], "name": row["name"],
                "identity": json.loads(row["identity_json"]), "hardware": json.loads(row["hardware_json"]),
                "interfaces": json.loads(row["interfaces_json"]), "first_seen": row["first_seen"],
                "last_seen": row["last_seen"]}

    def add_discovery(self, device_id: str, category: str, content: Any,
                      confidence: str = "hypothesis", source: str = "agent") -> dict[str, Any]:
        if confidence not in {"hypothesis", "confirmed"}:
            raise ValueError("confidence must be 'hypothesis' or 'confirmed'")
        with self._connect() as con:
            row = con.execute("SELECT device_id FROM devices WHERE device_id=? OR fingerprint=?", (device_id, device_id)).fetchone()
            if not row:
                raise KeyError(f"Unknown device: {device_id}")
            cur = con.execute("INSERT INTO discoveries(device_id,category,content_json,confidence,source,created_at) VALUES(?,?,?,?,?,?)",
                              (row["device_id"], category, json.dumps(content, default=str), confidence, source, utc_now()))
            return {"discovery_id": cur.lastrowid, "device_id": row["device_id"], "category": category,
                    "content": content, "confidence": confidence, "source": source}

    def add_experiment(self, device_id: str, interface_id: str | None, operation: str,
                       request: Any, response: Any, success: bool) -> None:
        keep_payloads = os.environ.get("UDMCP_STORE_PAYLOADS", "false").lower() in {"1", "true", "yes"}
        request = self._sanitize_audit(request, keep_payloads)
        response = self._sanitize_audit(response, keep_payloads)
        with self._connect() as con:
            row = con.execute("SELECT device_id FROM devices WHERE device_id=? OR fingerprint=?", (device_id, device_id)).fetchone()
            if not row:
                return
            con.execute("INSERT INTO experiments(device_id,interface_id,operation,request_json,response_json,success,created_at) VALUES(?,?,?,?,?,?,?)",
                        (row["device_id"], interface_id, operation, json.dumps(request, default=str),
                         json.dumps(response, default=str), int(success), utc_now()))

    @classmethod
    def _sanitize_audit(cls, value: Any, keep_payloads: bool, key: str = "") -> Any:
        """Keep audit metadata by default while redacting payloads and credentials."""
        if isinstance(value, dict):
            result = {}
            for child_key, child in value.items():
                lowered = child_key.lower()
                if any(secret in lowered for secret in ("password", "token", "secret", "pairing_code")):
                    result[child_key] = "[redacted]"
                elif lowered in {"data_hex", "payload_hex", "raw_bytes"} and isinstance(child, str):
                    try:
                        raw = bytes.fromhex(child) if lowered.endswith("_hex") else child.encode("utf-8")
                    except ValueError:
                        raw = child.encode("utf-8")
                    result[child_key] = child if keep_payloads else {
                        "redacted": True, "length_bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                else:
                    result[child_key] = cls._sanitize_audit(child, keep_payloads, child_key)
            return result
        if isinstance(value, list):
            return [cls._sanitize_audit(item, keep_payloads, key) for item in value]
        return value

    def purge_history(self, retention_days: int | None = 30) -> dict[str, int]:
        """Remove old communication/event history; None clears history while preserving profiles."""
        if retention_days is not None and (not isinstance(retention_days, int) or retention_days < 0):
            raise ValueError("retention_days must be a non-negative integer or null")
        with self._connect() as con:
            if retention_days is None:
                experiments = con.execute("DELETE FROM experiments").rowcount
                events = con.execute("DELETE FROM device_events").rowcount
                snapshots = con.execute("DELETE FROM device_snapshots").rowcount
            else:
                from datetime import datetime, timedelta, timezone
                before = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat(timespec="seconds")
                experiments = con.execute("DELETE FROM experiments WHERE created_at < ?", (before,)).rowcount
                events = con.execute("DELETE FROM device_events WHERE created_at < ?", (before,)).rowcount
                snapshots = con.execute("DELETE FROM device_snapshots WHERE observed_at < ?", (before,)).rowcount
            return {"experiments": max(0, experiments), "events": max(0, events),
                    "snapshots": max(0, snapshots)}

    def delete_experiment(self, device_id: str, experiment_id: int) -> bool:
        """Delete one recorded communication experiment for a device by its ID.

        Granular deletion of history without removing the whole device profile.
        """
        with self._connect() as con:
            row = con.execute("SELECT device_id FROM devices WHERE device_id=? OR fingerprint=?",
                              (device_id, device_id)).fetchone()
            if not row:
                return False
            did = row["device_id"]
            cursor = con.execute("DELETE FROM experiments WHERE experiment_id=? AND device_id=?",
                                 (experiment_id, did))
            return cursor.rowcount > 0

    def get_knowledge(self, device_id: str) -> dict[str, Any]:
        with self._connect() as con:
            row = con.execute("SELECT device_id FROM devices WHERE device_id=? OR fingerprint=?", (device_id, device_id)).fetchone()
            if not row:
                raise KeyError(f"Unknown device: {device_id}")
            did = row["device_id"]
            discoveries = con.execute("SELECT * FROM discoveries WHERE device_id=? ORDER BY discovery_id", (did,))
            experiments = con.execute("SELECT * FROM experiments WHERE device_id=? ORDER BY experiment_id DESC LIMIT 100", (did,))
            snapshots = con.execute("SELECT * FROM device_snapshots WHERE device_id=? ORDER BY snapshot_id DESC LIMIT 50", (did,))
            events = con.execute("SELECT * FROM device_events WHERE device_id=? ORDER BY event_id DESC LIMIT 100", (did,))
            return {"discoveries": [{"id": r["discovery_id"], "category": r["category"],
                    "content": json.loads(r["content_json"]), "confidence": r["confidence"],
                    "source": r["source"], "created_at": r["created_at"]} for r in discoveries],
                "experiments": [{"id": r["experiment_id"], "interface_id": r["interface_id"],
                    "operation": r["operation"], "request": json.loads(r["request_json"]),
                    "response": json.loads(r["response_json"]) if r["response_json"] else None,
                    "success": bool(r["success"]), "created_at": r["created_at"]} for r in experiments],
                "snapshots": [{"id": r["snapshot_id"], "configuration": json.loads(r["snapshot_json"]),
                    "observed_at": r["observed_at"]} for r in snapshots],
                "events": [{"id": r["event_id"], "device_id": r["device_id"],
                    "type": r["event_type"], "details": json.loads(r["details_json"]),
                    "created_at": r["created_at"]} for r in events]}

    def add_event(self, device_id: str, event_type: str, details: Any) -> int:
        with self._connect() as con:
            cur = con.execute("INSERT INTO device_events(device_id,event_type,details_json,created_at) VALUES(?,?,?,?)",
                              (device_id, event_type, json.dumps(details, default=str), utc_now()))
            return int(cur.lastrowid)

    def list_events(self, after_id: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute("SELECT * FROM device_events WHERE event_id>? ORDER BY event_id LIMIT ?",
                               (after_id, max(1, min(limit, 500))))
            return [{"id": r["event_id"], "device_id": r["device_id"],
                     "type": r["event_type"], "details": json.loads(r["details_json"]),
                     "created_at": r["created_at"]} for r in rows]

    def export_device(self, device_id: str) -> dict[str, Any]:
        device = self.get_device(device_id)
        if device is None:
            raise KeyError(f"Unknown device: {device_id}")
        return {**device, **self.get_knowledge(device_id)}

    def create_group(self, name: str, selector: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise ValueError("name must contain between 1 and 120 characters")
        if not isinstance(selector, dict) or not selector:
            raise ValueError("selector must be a non-empty object")
        now = utc_now()
        group_id = f"group-{uuid.uuid4().hex[:16]}"
        with self._connect() as con:
            con.execute("INSERT INTO device_groups VALUES (?,?,?,?,?)",
                        (group_id, name.strip(), json.dumps(selector, ensure_ascii=False), now, now))
        return {"group_id": group_id, "name": name.strip(), "selector": selector,
                "created_at": now, "updated_at": now}

    def get_group(self, group_id: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM device_groups WHERE group_id=?", (group_id,)).fetchone()
        return self._group_row(row) if row else None

    def list_groups(self) -> list[dict[str, Any]]:
        with self._connect() as con:
            return [self._group_row(row) for row in con.execute(
                "SELECT * FROM device_groups ORDER BY name COLLATE NOCASE")]

    def delete_group(self, group_id: str) -> bool:
        with self._connect() as con:
            cursor = con.execute("DELETE FROM device_groups WHERE group_id=?", (group_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _group_row(row: sqlite3.Row) -> dict[str, Any]:
        return {"group_id": row["group_id"], "name": row["name"],
                "selector": json.loads(row["selector_json"]),
                "created_at": row["created_at"], "updated_at": row["updated_at"]}

