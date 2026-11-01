"""Transport adapters. Optional dependencies are imported only when used."""

from .base import Adapter
from .usb import USBAdapter
from .serial import SerialAdapter
from .bluetooth import BluetoothAdapter
from .adb import ADBAdapter
from .network import NetworkAdapter
from .hid import HIDAdapter

__all__ = ["Adapter", "USBAdapter", "SerialAdapter", "BluetoothAdapter", "ADBAdapter", "NetworkAdapter", "HIDAdapter"]

