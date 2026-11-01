import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from universal_device_mcp.adapters.ios import IOSAdapter


class IOSAdapterTests(unittest.TestCase):
    def test_discovers_paired_device_from_usbmux_json(self):
        result = SimpleNamespace(returncode=0, stdout='["00008020-001234567890001E"]', stderr="")
        with patch("universal_device_mcp.adapters.ios.shutil.which", return_value="pymobiledevice3"), \
             patch("universal_device_mcp.adapters.ios.subprocess.run", return_value=result) as run:
            devices = IOSAdapter().discover()
        self.assertEqual(1, len(devices))
        self.assertEqual("ios", devices[0].transport)
        self.assertEqual("00008020-001234567890001E", devices[0].identity["udid"])
        self.assertEqual(["pymobiledevice3", "usbmux", "list", "--simple"], run.call_args.args[0])

    def test_falls_back_to_basic_usb_descriptors_without_unlock_or_trust(self):
        fake_device = SimpleNamespace(idVendor=0x05AC, idProduct=0x12A8, iSerialNumber=1,
                                      iProduct=2, iManufacturer=3, bus=1, address=4,
                                      port_numbers=[2, 1])
        usb_core = types.ModuleType("usb.core")
        usb_core.find = lambda **kwargs: [fake_device]
        usb_util = types.ModuleType("usb.util")
        usb_util.get_string = lambda _device, index: {1: "device-serial", 2: "iPhone", 3: "Apple"}[index]
        usb_package = types.ModuleType("usb")
        usb_package.core = usb_core
        usb_package.util = usb_util
        with patch("universal_device_mcp.adapters.ios.shutil.which", return_value=None), \
             patch.dict(sys.modules, {"usb": usb_package, "usb.core": usb_core, "usb.util": usb_util}):
            devices = IOSAdapter().discover()
        self.assertEqual(1, len(devices))
        self.assertEqual("usb_detected", devices[0].identity["state"])
        self.assertEqual("iPhone", devices[0].name)
        self.assertFalse(IOSAdapter().inspect(devices[0])["accessible"])

    def test_cli_is_pinned_to_selected_udid_without_a_shell(self):
        result = SimpleNamespace(returncode=0, stdout='{"apps": []}', stderr="")
        device = IOSAdapter()._udids('["A1"]')
        self.assertEqual(["A1"], device)
        from universal_device_mcp.models import Device
        target = Device("ios-A1", "ios", "iPhone", "ios:A1", identity={"udid": "A1"})
        with patch("universal_device_mcp.adapters.ios.shutil.which", return_value="pymobiledevice3"), \
             patch("universal_device_mcp.adapters.ios.subprocess.run", return_value=result) as run:
            response = IOSAdapter().communicate(target, "ios-cli", "execute",
                                                argv=["apps", "list"])
        self.assertEqual({"apps": []}, response["result"])
        self.assertEqual(["pymobiledevice3", "apps", "list", "--udid", "A1"],
                         run.call_args.args[0])
        self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_cli_cannot_override_target_udid(self):
        from universal_device_mcp.models import Device
        target = Device("ios-A1", "ios", "iPhone", "ios:A1", identity={"udid": "A1"})
        with self.assertRaisesRegex(ValueError, "Do not override"):
            IOSAdapter().communicate(target, "ios-cli", "execute",
                                     argv=["apps", "list", "--udid", "other-device"])

    def test_uses_current_python_when_entrypoint_is_not_on_path(self):
        with patch("universal_device_mcp.adapters.ios.shutil.which", return_value=None), \
             patch("universal_device_mcp.adapters.ios.importlib.util.find_spec", return_value=object()):
            self.assertEqual([sys.executable, "-m", "pymobiledevice3"],
                             IOSAdapter._command_prefix())


if __name__ == "__main__":
    unittest.main()
