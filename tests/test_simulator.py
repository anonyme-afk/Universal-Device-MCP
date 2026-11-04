import tempfile
import unittest
from pathlib import Path

from universal_device_mcp.adapters.simulator import SimulatorAdapter
from universal_device_mcp.memory import DeviceMemory
from universal_device_mcp.server import DeviceService


class RecordingSimulator(SimulatorAdapter):
    def __init__(self):
        self.writes = []

    def communicate(self, device, interface_id, operation, data=None, **options):
        if operation in {"write", "send", "communicate", "control_write", "execute"}:
            self.writes.append((device.device_id, operation, data))
        return super().communicate(device, interface_id, operation, data=data, **options)


class SimulatorTests(unittest.TestCase):
    def test_ten_identical_models_are_read_concurrently_and_remain_distinct(self):
        with tempfile.TemporaryDirectory() as folder:
            service = DeviceService(DeviceMemory(Path(folder) / "devices.sqlite3"), [SimulatorAdapter()])
            devices = service.discover(["simulator"])["devices"]
            self.assertEqual(10, len(devices))
            self.assertEqual(devices[0]["identity"]["model"], devices[1]["identity"]["model"])
            result = service.communicate_many([
                {"device_id": device["device_id"], "interface_id": "telemetry"}
                for device in devices
            ], "read")
            self.assertEqual(10, result["completed"])
            self.assertTrue(all(item["ok"] for item in result["results"]))
            self.assertEqual({f"{index:02d}" for index in range(1, 11)},
                             {item["response"]["device"] for item in result["results"]})

    def test_disconnected_target_gets_its_own_error_without_dropping_other_results(self):
        with tempfile.TemporaryDirectory() as folder:
            service = DeviceService(DeviceMemory(Path(folder) / "devices.sqlite3"), [SimulatorAdapter()])
            devices = service.discover(["simulator"])["devices"]
            service._connected.pop(devices[0]["device_id"])
            result = service.communicate_many([
                {"device_id": device["device_id"], "interface_id": "telemetry"}
                for device in devices[:2]
            ], "read")
            self.assertEqual(2, len(result["results"]))
            self.assertEqual({False, True}, {item["ok"] for item in result["results"]})

    def test_batch_writes_are_rejected_before_target_access(self):
        with tempfile.TemporaryDirectory() as folder:
            service = DeviceService(DeviceMemory(Path(folder) / "devices.sqlite3"), [SimulatorAdapter()])
            with self.assertRaisesRegex(PermissionError, "only permits read/receive"):
                service.communicate_many([{"device_id": "unknown", "interface_id": "telemetry"}], "write")

    def test_dynamic_group_reads_matching_identical_devices_and_keeps_per_device_results(self):
        with tempfile.TemporaryDirectory() as folder:
            service = DeviceService(DeviceMemory(Path(folder) / "devices.sqlite3"), [SimulatorAdapter()])
            service.discover(["simulator"])
            group = service.memory.create_group("demo sensors", {"model": "UDMCP-Sensor"})
            resolved = service.inspect_group(group["group_id"])
            self.assertEqual(10, resolved["member_count"])
            result = service.read_group(group["group_id"], "telemetry")
            self.assertEqual(10, result["completed"])
            self.assertTrue(all(target["ok"] for target in result["results"]))

    def test_group_selector_can_include_offline_profiles_and_reports_read_errors_separately(self):
        with tempfile.TemporaryDirectory() as folder:
            service = DeviceService(DeviceMemory(Path(folder) / "devices.sqlite3"), [SimulatorAdapter()])
            devices = service.discover(["simulator"])["devices"]
            group = service.memory.create_group("one sensor", {"device_ids": [devices[0]["device_id"]]})
            service._connected.pop(devices[0]["device_id"])
            resolved = service.inspect_group(group["group_id"])
            self.assertEqual(0, resolved["connected_count"])
            result = service.read_group(group["group_id"], "telemetry")
            self.assertFalse(result["results"][0]["ok"])

    def test_group_write_is_frozen_policy_checked_one_time_and_reports_partial_results(self):
        import json
        import os
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as folder:
            adapter = RecordingSimulator()
            service = DeviceService(DeviceMemory(Path(folder) / "devices.sqlite3"), [adapter])
            devices = service.discover(["simulator"])["devices"]
            group = service.memory.create_group("authorized sensors", {"model": "UDMCP-Sensor"})
            policy = Path(folder) / "policy.json"
            policy.write_text(json.dumps({"allowed_operations": [
                {"transport": "simulator", "device_id": device["device_id"],
                 "interface_id": "telemetry", "operation": "write"}
                for device in devices
            ]}), encoding="utf-8")
            with patch.dict(os.environ, {"UDMCP_POLICY": str(policy)}):
                preview = service.prepare_group_write(group["group_id"], "telemetry", "write", "CAFE")
                self.assertEqual(10, preview["target_count"])
                self.assertTrue(preview["requires_client_elicitation"])
                self.assertEqual([], adapter.writes)
                frozen_plan = service.pending_group_write(preview["approval_id"])
                frozen_plan["targets"].pop()
                self.assertEqual(10, len(service.pending_group_write(preview["approval_id"])["targets"]))
                result = service.execute_group_write(preview["approval_id"])
                self.assertEqual(10, result["completed"])
                self.assertEqual(10, len(adapter.writes))
                with self.assertRaisesRegex(KeyError, "already used"):
                    service.execute_group_write(preview["approval_id"])

    def test_group_write_preview_fails_closed_without_exact_allow_rules(self):
        with tempfile.TemporaryDirectory() as folder:
            adapter = RecordingSimulator()
            service = DeviceService(DeviceMemory(Path(folder) / "devices.sqlite3"), [adapter])
            service.discover(["simulator"])
            group = service.memory.create_group("all sensors", {"model": "UDMCP-Sensor"})
            with self.assertRaisesRegex(
                PermissionError, r"Blocked by .* policy for .*/write"
            ):
                service.prepare_group_write(group["group_id"], "telemetry", "write", "CAFE")
            self.assertEqual([], adapter.writes)

if __name__ == "__main__":
    unittest.main()
