import unittest
from types import SimpleNamespace
from unittest.mock import patch

from universal_device_mcp.adapters.adb import ADBAdapter


class ADBAdapterTests(unittest.TestCase):
    def test_reports_unauthorized_devices_without_exposing_a_shell(self):
        output = """List of devices attached
phone-one unauthorized usb:1-2 product:Demo model:Demo_Phone
phone-two device usb:1-3 product:Demo model:Authorized_Phone
"""
        result = SimpleNamespace(returncode=0, stdout=output, stderr="")
        with patch("universal_device_mcp.adapters.adb.shutil.which", return_value="adb"), \
             patch("universal_device_mcp.adapters.adb.subprocess.run", return_value=result):
            devices = ADBAdapter().discover()
        self.assertEqual(2, len(devices))
        unauthorized = next(device for device in devices if device.identity["serial"] == "phone-one")
        authorized = next(device for device in devices if device.identity["serial"] == "phone-two")
        self.assertEqual("unauthorized", unauthorized.identity["state"])
        self.assertEqual([], unauthorized.interfaces)
        self.assertFalse(ADBAdapter().inspect(unauthorized)["accessible"])
        self.assertEqual("device", authorized.identity["state"])
        self.assertEqual("shell", authorized.interfaces[0]["id"])

    def test_wireless_discovery_parses_only_adb_tls_services(self):
        output = """List of discovered mdns services
adb-test _adb-tls-pairing._tcp 192.168.1.20:37123
adb-test _adb-tls-connect._tcp 192.168.1.20:44643
printer _ipp._tcp 192.168.1.40:631
"""
        result = SimpleNamespace(returncode=0, stdout=output, stderr="")
        with patch("universal_device_mcp.adapters.adb.shutil.which", return_value="adb"), \
             patch("universal_device_mcp.adapters.adb.subprocess.run", return_value=result):
            services = ADBAdapter().discover_wireless_services()
        self.assertEqual(["pairing", "connect"], [service["kind"] for service in services])
        self.assertEqual("192.168.1.20:37123", services[0]["endpoint"])

    def test_wireless_pairing_code_is_passed_via_stdin_only(self):
        mdns = SimpleNamespace(returncode=0, stdout=(
            "adb-test _adb-tls-pairing._tcp 192.168.1.20:37123\n"), stderr="")
        paired = SimpleNamespace(returncode=0, stdout="Successfully paired", stderr="")
        with patch("universal_device_mcp.adapters.adb.shutil.which", return_value="adb"), \
             patch("universal_device_mcp.adapters.adb.subprocess.run", side_effect=[mdns, paired]) as run:
            result = ADBAdapter().pair_wireless("192.168.1.20:37123", "123456")
        self.assertTrue(result["paired"])
        self.assertNotIn("123456", run.call_args.args[0])
        self.assertEqual("123456\n", run.call_args.kwargs["input"])


if __name__ == "__main__":
    unittest.main()
