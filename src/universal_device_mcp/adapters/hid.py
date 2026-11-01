"""USB HID report adapter using the cross-platform hidapi bindings."""

from __future__ import annotations

import hashlib
import threading
from typing import Any

from ..models import Device
from .base import Adapter


class HIDAdapter(Adapter):
    transport = "hid"

    def __init__(self) -> None:
        self._session_lock = threading.Lock()
        self._open_paths: set[str] = set()

    @staticmethod
    def _hid():
        try:
            import hid
        except ImportError as exc:
            raise RuntimeError("USB HID support requires: pip install universal-device-mcp[hid]") from exc
        return hid

    def _open_handle(self, device: Device) -> Any:
        path_hex = device.identity["path_hex"]
        with self._session_lock:
            if path_hex in self._open_paths:
                raise RuntimeError("HID interface already has an open session; reuse it or close it first")
            self._open_paths.add(path_hex)
        try:
            handle = self._hid().device()
            handle.open_path(bytes.fromhex(path_hex))
            return handle
        except Exception:
            with self._session_lock:
                self._open_paths.discard(path_hex)
            raise

    def _close_handle(self, device: Device, handle: Any) -> None:
        path_hex = device.identity["path_hex"]
        try:
            handle.close()
        finally:
            with self._session_lock:
                self._open_paths.discard(path_hex)

    def discover(self) -> list[Device]:
        hid = self._hid()
        devices: list[Device] = []
        for item in hid.enumerate():
            path = item.get("path")
            if not path:
                continue
            path_bytes = path if isinstance(path, bytes) else str(path).encode("utf-8")
            vid, pid = int(item.get("vendor_id") or 0), int(item.get("product_id") or 0)
            serial = item.get("serial_number") or ""
            fingerprint = f"hid:{vid:04x}:{pid:04x}:{serial + ':' if serial else ''}{path_bytes.hex()}"
            product = item.get("product_string") or f"HID {vid:04x}:{pid:04x}"
            devices.append(Device(
                device_id=f"hid-{hashlib.sha1(fingerprint.encode()).hexdigest()[:12]}",
                transport=self.transport, name=product, fingerprint=fingerprint,
                identity={"vendor_id": vid, "product_id": pid, "manufacturer": item.get("manufacturer_string"),
                          "product": product, "serial_number": serial or None, "path_hex": path_bytes.hex(),
                          "fingerprint_basis": "vendor_product_serial_and_hid_path" if serial
                                              else "vendor_product_hid_path"},
                hardware={"release_number": item.get("release_number"),
                          "usage_page": item.get("usage_page"), "usage": item.get("usage"),
                          "interface_number": item.get("interface_number"),
                          "bus_type": item.get("bus_type")},
                interfaces=[{"id": "hid-report", "kind": "hid-report",
                             "usage_page": item.get("usage_page"), "usage": item.get("usage")}]))
        return devices

    def communicate(self, device: Device, interface_id: str, operation: str,
                    data: bytes | None = None, **options: Any) -> dict[str, Any]:
        if interface_id != "hid-report":
            raise ValueError("HID interface_id must be 'hid-report'")
        if operation == "inspect":
            return {"identity": device.identity, "hardware": device.hardware}
        if operation not in {"read", "receive", "write", "send"}:
            raise ValueError("HID operation must be inspect, read, receive, write or send")
        self._hid()
        length = int(options.get("length", 64))
        timeout_ms = int(options.get("timeout_ms", 1000))
        if not 1 <= length <= 65_536:
            raise ValueError("HID read length must be between 1 and 65536")
        if not 0 <= timeout_ms <= 120_000:
            raise ValueError("timeout_ms must be between 0 and 120000")
        handle = options.pop("_session", None)
        owned = handle is None
        if owned:
            handle = self._open_handle(device)
        try:
            if operation in {"read", "receive"}:
                report = handle.read(length, timeout_ms)
                payload = bytes(report)
                return {"data_hex": payload.hex(), "data_length": len(payload)}
            if not data:
                raise ValueError("HID write requires a non-empty data_hex payload")
            return {"bytes_written": int(handle.write(list(data)))}
        finally:
            if owned:
                self._close_handle(device, handle)

    def open_interface(self, device: Device, interface_id: str, **options: Any) -> Any:
        if interface_id != "hid-report":
            raise ValueError("HID interface_id must be 'hid-report'")
        return self._open_handle(device)

    def close_interface(self, device: Device, interface_id: str, session: Any) -> None:
        self._close_handle(device, session)

