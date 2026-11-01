import tempfile
import unittest
from pathlib import Path

from universal_device_mcp.adapters.simulator import SimulatorAdapter
from universal_device_mcp.memory import DeviceMemory
from universal_device_mcp.server import DeviceService


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


if __name__ == "__main__":
    unittest.main()
