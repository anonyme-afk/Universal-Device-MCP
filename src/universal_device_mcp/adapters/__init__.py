"""Transport adapters. Optional dependencies are imported only when used."""

from .adb import ADBAdapter
from .base import Adapter
from .bluetooth import BluetoothAdapter
from .hid import HIDAdapter
from .ios import IOSAdapter
from .network import NetworkAdapter
from .serial import SerialAdapter
from .simulator import SimulatorAdapter
from .usb import USBAdapter

__all__ = [
    "Adapter",
    "USBAdapter",
    "SerialAdapter",
    "BluetoothAdapter",
    "ADBAdapter",
    "NetworkAdapter",
    "HIDAdapter",
    "IOSAdapter",
    "SimulatorAdapter",
]