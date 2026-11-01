import unittest

from universal_device_mcp.adapters.usb import USBAdapter
from universal_device_mcp.models import Device


class FakeUSBDevice:
    def __init__(self, bus, address, serial=None):
        self.bus = bus
        self.address = address
        self.serial_number = serial


class FakeUSBCore:
    def __init__(self, devices):
        self.devices = devices

    def find(self, **kwargs):
        return self.devices


class USBAdapterTests(unittest.TestCase):
    def test_unserialized_usb_device_is_selected_by_current_bus_address(self):
        expected = FakeUSBDevice(1, 8)
        other = FakeUSBDevice(1, 9)
        profile = Device("usb-test", "usb", "same-model", "usb:1234:5678:port",
                         identity={"vendor_id": 0x1234, "product_id": 0x5678},
                         hardware={"bus": 1, "address": 8})
        selected = USBAdapter._find_device(FakeUSBCore([expected, other]), profile)
        self.assertIs(expected, selected)

    def test_ambiguous_usb_identity_is_rejected(self):
        profile = Device("usb-test", "usb", "same-model", "usb:1234:5678:unknown",
                         identity={"vendor_id": 0x1234, "product_id": 0x5678}, hardware={})
        with self.assertRaisesRegex(RuntimeError, "one exact USB device"):
            USBAdapter._find_device(FakeUSBCore([FakeUSBDevice(None, None), FakeUSBDevice(None, None)]), profile)


if __name__ == "__main__":
    unittest.main()
