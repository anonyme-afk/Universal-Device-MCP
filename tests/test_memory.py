import tempfile
import unittest
from pathlib import Path

from universal_device_mcp.memory import DeviceMemory
from universal_device_mcp.models import Device


class DeviceMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.memory = DeviceMemory(Path(self.temp.name) / "devices.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def test_device_round_trip_and_fingerprint_reuse(self):
        first = Device("device-a", "serial", "Board", "serial:abc", identity={"port": "COM3"})
        saved = self.memory.save_device(first)
        again = Device("different-id", "serial", "Updated board", "serial:abc", identity={"port": "COM4"})
        updated = self.memory.save_device(again)
        self.assertEqual(saved["device_id"], updated["device_id"])
        self.assertEqual("Updated board", self.memory.get_device("serial:abc")["name"])
        self.assertEqual("COM4", self.memory.get_device(saved["device_id"])["identity"]["port"])

    def test_discoveries_keep_confidence_and_history(self):
        self.memory.save_device(Device("device-a", "usb", "Sensor", "usb:1234"))
        self.memory.add_discovery("device-a", "protocol", {"name": "unknown"})
        self.memory.add_discovery("device-a", "protocol", {"name": "UART"}, "confirmed", "datasheet")
        knowledge = self.memory.get_knowledge("device-a")
        self.assertEqual(["hypothesis", "confirmed"], [d["confidence"] for d in knowledge["discoveries"]])

    def test_invalid_confidence_is_rejected(self):
        self.memory.save_device(Device("device-a", "usb", "Sensor", "usb:1234"))
        with self.assertRaises(ValueError):
            self.memory.add_discovery("device-a", "protocol", {}, "certain")

    def test_configuration_changes_are_snapshotted(self):
        first = Device("device-a", "usb", "Sensor", "usb:1234", hardware={"firmware": "1"})
        self.assertFalse(self.memory.save_device(first)["configuration_changed"])
        self.memory.save_device(first)
        changed = Device("device-a", "usb", "Sensor", "usb:1234", hardware={"firmware": "2"})
        self.assertTrue(self.memory.save_device(changed)["configuration_changed"])
        snapshots = self.memory.get_knowledge("device-a")["snapshots"]
        self.assertEqual(2, len(snapshots))
        self.assertEqual({"firmware": "1"}, snapshots[-1]["configuration"]["hardware"])

    def test_connection_events_are_persistent_and_ordered(self):
        self.memory.save_device(Device("device-a", "serial", "Board", "serial:abc"))
        first = self.memory.add_event("device-a", "connected", {"transport": "serial"})
        self.memory.add_event("device-a", "disconnected", {"transport": "serial"})
        events = self.memory.list_events(after_id=first - 1)
        self.assertEqual(["connected", "disconnected"], [event["type"] for event in events])

    def test_profile_update_merges_metadata_and_preserves_identity(self):
        self.memory.save_device(Device("device-a", "usb", "Sensor", "usb:1234",
                                       identity={"serial_number": "abc"}, hardware={"revision": 1}))
        updated = self.memory.update_device("device-a", {
            "name": "Desk sensor", "identity": {"model": "S1"}, "hardware": {"revision": 2}})
        self.assertEqual("usb:1234", updated["fingerprint"])
        self.assertEqual("Desk sensor", updated["name"])
        self.assertEqual({"serial_number": "abc", "model": "S1"}, updated["identity"])
        self.assertEqual({"revision": 2}, updated["hardware"])
        self.assertTrue(updated["configuration_changed"])

    def test_runtime_usb_address_and_ble_rssi_do_not_create_snapshots(self):
        first = Device("device-a", "usb", "Sensor", "usb:1234",
                       identity={"address": 1, "rssi": -40}, hardware={"port_numbers": [2, 3]})
        self.memory.save_device(first)
        refreshed = Device("device-a", "usb", "Sensor", "usb:1234",
                           identity={"address": 7, "rssi": -62}, hardware={"port_numbers": [2, 3]})
        result = self.memory.save_device(refreshed)
        self.assertFalse(result["configuration_changed"])
        self.assertEqual(1, len(self.memory.get_knowledge("device-a")["snapshots"]))

    def test_adb_authorization_state_does_not_look_like_hardware_reconfiguration(self):
        unauthorized = Device("adb-phone", "adb", "Phone", "adb:serial",
                              identity={"serial": "serial", "state": "unauthorized"})
        self.memory.save_device(unauthorized)
        authorized = Device("adb-phone", "adb", "Phone", "adb:serial",
                            identity={"serial": "serial", "state": "device"},
                            interfaces=[{"id": "shell", "kind": "adb-shell"}])
        refreshed = self.memory.save_device(authorized)
        self.assertFalse(refreshed["configuration_changed"])
        self.assertEqual(1, len(self.memory.get_knowledge("adb-phone")["snapshots"]))

    def test_ios_unlocking_and_trusting_host_does_not_look_like_hardware_reconfiguration(self):
        locked = Device("ios-phone", "ios", "Apple USB device", "ios:udid-1",
                        identity={"serial": "udid-1", "state": "usb_detected"},
                        hardware={"vendor_id": "0x05ac", "product_id": "0x12a8"},
                        interfaces=[{"id": "usb-descriptors"}])
        self.memory.save_device(locked)
        trusted = Device("ios-phone", "ios", "iPhone", "ios:udid-1",
                         identity={"udid": "udid-1", "state": "connected"},
                         hardware={"vendor_id": "0x05ac", "product_id": "0x12a8"},
                         interfaces=[{"id": "lockdown"}, {"id": "ios-cli"}])
        refreshed = self.memory.save_device(trusted)
        self.assertFalse(refreshed["configuration_changed"])
        self.assertEqual(1, len(self.memory.get_knowledge("ios-phone")["snapshots"]))


if __name__ == "__main__":
    unittest.main()
