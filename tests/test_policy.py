import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from universal_device_mcp.memory import DeviceMemory
from universal_device_mcp.models import Device


class FakeAdapter:
    transport = "fake"

    def __init__(self):
        self.calls = 0
        self.connected = True
        self.state = "device"

    def discover(self):
        return [Device("fake-device", self.transport, "Test device", f"{self.transport}:1",
                       identity={"state": self.state},
                       interfaces=[{"id": "shell", "kind": "adb-shell"}]
                       if self.transport == "adb" and self.state == "device" else [])] if self.connected else []

    def communicate(self, device, interface_id, operation, data=None, **options):
        self.calls += 1
        return {"sent": len(data or b""), "session_open": options.get("_session", {}).get("open")}

    def open_interface(self, device, interface_id, **options):
        return {"open": True}

    def close_interface(self, device, interface_id, session):
        session["open"] = False


class AccessPolicyTests(unittest.TestCase):
    def test_device_service_records_connect_and_disconnect(self):
        with tempfile.TemporaryDirectory() as folder:
            old_database = os.environ.get("UDMCP_DATABASE")
            os.environ["UDMCP_DATABASE"] = str(Path(folder) / "default.sqlite3")
            from universal_device_mcp.server import DeviceService
            memory = DeviceMemory(Path(folder) / "devices.sqlite3")
            adapter = FakeAdapter()
            service = DeviceService(memory=memory, adapters=[adapter])
            service.discover()
            adapter.connected = False
            service.discover()
            events = memory.list_events()
            self.assertEqual(["connected", "disconnected"], [event["type"] for event in events])
            if old_database is None:
                os.environ.pop("UDMCP_DATABASE", None)
            else:
                os.environ["UDMCP_DATABASE"] = old_database

    def test_access_state_change_is_not_misreported_as_hardware_change(self):
        with tempfile.TemporaryDirectory() as folder:
            old_database = os.environ.get("UDMCP_DATABASE")
            os.environ["UDMCP_DATABASE"] = str(Path(folder) / "default.sqlite3")
            from universal_device_mcp.server import DeviceService
            memory = DeviceMemory(Path(folder) / "devices.sqlite3")
            adapter = FakeAdapter()
            adapter.transport = "adb"
            adapter.state = "unauthorized"
            service = DeviceService(memory=memory, adapters=[adapter])
            service.discover()
            adapter.state = "device"
            updated = service.discover()["devices"][0]
            self.assertFalse(updated["configuration_changed"])
            events = memory.list_events()
            self.assertEqual(["connected", "state_changed"], [event["type"] for event in events])
            if old_database is None:
                os.environ.pop("UDMCP_DATABASE", None)
            else:
                os.environ["UDMCP_DATABASE"] = old_database

    def test_denied_operation_is_logged_and_not_sent(self):
        with tempfile.TemporaryDirectory() as folder:
            old_database = os.environ.get("UDMCP_DATABASE")
            os.environ["UDMCP_DATABASE"] = str(Path(folder) / "default.sqlite3")
            from universal_device_mcp.server import DeviceService
            memory = DeviceMemory(Path(folder) / "devices.sqlite3")
            adapter = FakeAdapter()
            service = DeviceService(memory=memory, adapters=[adapter])
            device = service.discover()["devices"][0]
            policy_path = Path(folder) / "policy.json"
            policy_path.write_text(json.dumps({"denied_operations": [
                {"transport": "fake", "operation": "write"}]}), encoding="utf-8")
            with patch.dict(os.environ, {"UDMCP_POLICY": str(policy_path)}):
                with self.assertRaisesRegex(RuntimeError, "Blocked by local policy"):
                    service.communicate(device["device_id"], "test", "write", "CAFE")
            self.assertEqual(0, adapter.calls)
            experiments = memory.get_knowledge(device["device_id"])["experiments"]
            self.assertFalse(experiments[0]["success"])
            if old_database is None:
                os.environ.pop("UDMCP_DATABASE", None)
            else:
                os.environ["UDMCP_DATABASE"] = old_database

    def test_communicate_payload_obeys_local_write_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            old_database = os.environ.get("UDMCP_DATABASE")
            os.environ["UDMCP_DATABASE"] = str(Path(folder) / "default.sqlite3")
            from universal_device_mcp.server import DeviceService
            memory = DeviceMemory(Path(folder) / "devices.sqlite3")
            adapter = FakeAdapter()
            service = DeviceService(memory=memory, adapters=[adapter])
            device = service.discover()["devices"][0]
            policy_path = Path(folder) / "policy.json"
            policy_path.write_text(json.dumps({"max_write_bytes": 1, "allowed_operations": [
                {"transport": "fake", "device_id": device["device_id"],
                 "interface_id": "test", "operation": "communicate"}]}), encoding="utf-8")
            with patch.dict(os.environ, {"UDMCP_POLICY": str(policy_path)}):
                with self.assertRaisesRegex(RuntimeError, "local policy limit is 1"):
                    service.communicate(device["device_id"], "test", "communicate", "CAFE")
            self.assertEqual(0, adapter.calls)
            if old_database is None:
                os.environ.pop("UDMCP_DATABASE", None)
            else:
                os.environ["UDMCP_DATABASE"] = old_database

    def test_interface_session_open_communicate_and_close(self):
        with tempfile.TemporaryDirectory() as folder:
            old_database = os.environ.get("UDMCP_DATABASE")
            os.environ["UDMCP_DATABASE"] = str(Path(folder) / "default.sqlite3")
            from universal_device_mcp.server import DeviceService
            memory = DeviceMemory(Path(folder) / "devices.sqlite3")
            adapter = FakeAdapter()
            service = DeviceService(memory=memory, adapters=[adapter])
            device = service.discover()["devices"][0]
            policy_path = Path(folder) / "policy.json"
            policy_path.write_text(json.dumps({"allowed_operations": [
                {"transport": "fake", "device_id": device["device_id"],
                 "interface_id": "test", "operation": "open"},
                {"transport": "fake", "device_id": device["device_id"],
                 "interface_id": "test", "operation": "write"}]}), encoding="utf-8")
            with patch.dict(os.environ, {"UDMCP_POLICY": str(policy_path)}):
                opened = service.open_interface(device["device_id"], "test")
                result = service.communicate(device["device_id"], "test", "write", "CAFE",
                                             session_id=opened["session_id"])
            self.assertTrue(result["session_open"])
            experiment = memory.get_knowledge(device["device_id"])["experiments"][0]
            self.assertEqual({"redacted": True, "length_bytes": 2,
                              "sha256": hashlib.sha256(bytes.fromhex("CAFE")).hexdigest()},
                             experiment["request"]["data_hex"])
            service.close_interface(opened["session_id"])
            self.assertEqual(0, len(service._sessions))
            if old_database is None:
                os.environ.pop("UDMCP_DATABASE", None)
            else:
                os.environ["UDMCP_DATABASE"] = old_database

    def test_stale_profile_cannot_be_used_as_a_live_target(self):
        with tempfile.TemporaryDirectory() as folder:
            old_database = os.environ.get("UDMCP_DATABASE")
            os.environ["UDMCP_DATABASE"] = str(Path(folder) / "default.sqlite3")
            from universal_device_mcp.server import DeviceService
            memory = DeviceMemory(Path(folder) / "devices.sqlite3")
            adapter = FakeAdapter()
            service = DeviceService(memory=memory, adapters=[adapter])
            device = service.discover()["devices"][0]
            service._connected.clear()
            inspection = service.inspect(device["device_id"])
            self.assertFalse(inspection["inspection"]["live_inspection"])
            with self.assertRaisesRegex(RuntimeError, "not currently connected"):
                service.communicate(device["device_id"], "test", "write", "CAFE")
            if old_database is None:
                os.environ.pop("UDMCP_DATABASE", None)
            else:
                os.environ["UDMCP_DATABASE"] = old_database


if __name__ == "__main__":
    unittest.main()
