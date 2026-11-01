from __future__ import annotations

import hashlib
import threading
from collections import Counter
from typing import Any

from ..models import Device
from .base import Adapter


class USBAdapter(Adapter):
    transport = "usb"
    _TRANSFER_TYPES = {0: "control", 1: "isochronous", 2: "bulk", 3: "interrupt"}

    def __init__(self) -> None:
        self._session_lock = threading.Lock()
        self._open_interfaces: set[tuple[str, int, int]] = set()

    @staticmethod
    def _to_int(value: Any) -> int:
        return int(value, 0) if isinstance(value, str) else int(value)

    def _usb(self):
        try:
            import usb.core
        except ImportError as exc:
            raise RuntimeError("USB support requires the optional 'usb' extra: pip install universal-device-mcp[usb]") from exc
        return usb.core

    @staticmethod
    def _find_device(core: Any, device: Device) -> Any:
        """Resolve the exact enumerated unit; VID/PID alone is not a safe selector."""
        vid = int(device.identity["vendor_id"])
        pid = int(device.identity["product_id"])
        serial = device.identity.get("serial_number")
        matches = list(core.find(find_all=True, idVendor=vid, idProduct=pid) or [])
        if serial:
            matches = [item for item in matches if USBAdapter._safe_string(item, "serial_number") == serial]
            expected_ports = device.hardware.get("port_numbers")
            if expected_ports:
                matches = [item for item in matches
                           if list(getattr(item, "port_numbers", []) or []) == list(expected_ports)]
        else:
            expected_bus = device.hardware.get("bus")
            expected_address = device.hardware.get("address")
            matches = [item for item in matches
                       if getattr(item, "bus", None) == expected_bus
                       and getattr(item, "address", None) == expected_address]
        if len(matches) != 1:
            raise RuntimeError("Could not resolve one exact USB device; rediscover it and select the current device_id")
        return matches[0]

    def discover(self) -> list[Device]:
        core = self._usb()
        devices = []
        raw_devices = list(core.find(find_all=True) or [])

        def location_for(dev: Any) -> tuple[list[int] | None, str]:
            ports = getattr(dev, "port_numbers", None)
            if not ports:
                port = getattr(dev, "port_number", None)
                ports = [port] if port is not None else None
            location = ".".join(str(part) for part in ports) if ports else f"{dev.bus}:{dev.address}"
            return ports, location

        base_fingerprints: list[str] = []
        for dev in raw_devices:
            serial = self._safe_string(dev, "serial_number")
            _, location = location_for(dev)
            base_fingerprints.append(f"usb:{int(dev.idVendor):04x}:{int(dev.idProduct):04x}:{serial or location}")
        duplicate_bases = {key for key, count in Counter(base_fingerprints).items() if count > 1}

        for dev, base_fingerprint in zip(raw_devices, base_fingerprints):
            vid, pid = int(dev.idVendor), int(dev.idProduct)
            serial = self._safe_string(dev, "serial_number")
            manufacturer = self._safe_string(dev, "manufacturer")
            product = self._safe_string(dev, "product") or f"USB {vid:04x}:{pid:04x}"
            port_numbers, location = location_for(dev)
            fingerprint_basis = "vendor_product_serial_and_topology" if serial and base_fingerprint in duplicate_bases else (
                "vendor_product_serial" if serial else (
                "vendor_product_topology" if port_numbers else "vendor_product_bus_address")
            )
            fingerprint = (f"{base_fingerprint}:port:{location}"
                           if base_fingerprint in duplicate_bases else base_fingerprint)
            interfaces = []
            configurations = []
            try:
                for cfg in dev:
                    configurations.append({"value": int(cfg.bConfigurationValue),
                                           "attributes": int(cfg.bmAttributes),
                                           "max_power_descriptor_units": int(cfg.bMaxPower)})
                    for intf in cfg:
                        endpoints = [{"address": int(ep.bEndpointAddress),
                                      "direction": "in" if ep.bEndpointAddress & 0x80 else "out",
                                      "transfer_type": int(ep.bmAttributes) & 0x03,
                                      "transfer_type_name": self._TRANSFER_TYPES.get(int(ep.bmAttributes) & 0x03, "reserved"),
                                      "max_packet_size": int(ep.wMaxPacketSize),
                                      "interval": int(ep.bInterval)} for ep in intf]
                        interfaces.append({"id": f"{cfg.bConfigurationValue}:{intf.bInterfaceNumber}:{intf.bAlternateSetting}",
                            "configuration": int(cfg.bConfigurationValue), "interface_number": int(intf.bInterfaceNumber),
                            "alternate_setting": int(intf.bAlternateSetting), "class": int(intf.bInterfaceClass),
                            "subclass": int(intf.bInterfaceSubClass), "protocol": int(intf.bInterfaceProtocol),
                            "description": self._safe_usb_string(dev, getattr(intf, "iInterface", 0)),
                            "endpoints": endpoints})
            except Exception as exc:
                interfaces.append({"inspection_error": str(exc)})
            devices.append(Device(device_id=f"usb-{vid:04x}-{pid:04x}-{hashlib.sha1(fingerprint.encode()).hexdigest()[:8]}",
                transport=self.transport, name=product, fingerprint=fingerprint,
                identity={"vendor_id": vid, "product_id": pid, "manufacturer": manufacturer, "product": product,
                          "serial_number": serial, "fingerprint_basis": fingerprint_basis},
                hardware={"bus": getattr(dev, "bus", None), "address": getattr(dev, "address", None),
                          "port_numbers": port_numbers,
                          "device_class": int(dev.bDeviceClass), "device_subclass": int(dev.bDeviceSubClass),
                          "device_protocol": int(dev.bDeviceProtocol), "usb_version": str(dev.bcdUSB),
                          "device_version": str(dev.bcdDevice),
                          "max_packet_size_zero": int(dev.bMaxPacketSize0),
                          "configuration_count": int(dev.bNumConfigurations),
                          "configurations": configurations}, interfaces=interfaces))
        return devices

    @staticmethod
    def _safe_string(dev: Any, key: str) -> str | None:
        try:
            return getattr(dev, key)
        except Exception:
            return None

    @staticmethod
    def _safe_usb_string(dev: Any, index: int) -> str | None:
        if not index:
            return None
        try:
            import usb.util
            return usb.util.get_string(dev, index)
        except Exception:
            return None

    @staticmethod
    def _ensure_configuration(dev: Any, intf: dict[str, Any], options: dict[str, Any]) -> None:
        target = int(intf["configuration"])
        try:
            active = dev.get_active_configuration()
            active_value = int(active.bConfigurationValue) if active is not None else None
        except Exception:
            active_value = None
        if active_value == target:
            return
        if options.get("set_configuration") is not True:
            raise RuntimeError(
                f"USB configuration {target} is not active; pass set_configuration=true to switch explicitly"
            )
        dev.set_configuration(target)

    def communicate(self, device: Device, interface_id: str, operation: str,
                    data: bytes | None = None, **options: Any) -> dict[str, Any]:
        core = self._usb()
        intf = next((i for i in device.interfaces if i.get("id") == interface_id), None)
        if intf is None:
            raise ValueError(f"Unknown USB interface: {interface_id}")
        if operation == "inspect":
            return {"interface": intf, "identity": device.identity, "hardware": device.hardware}
        if operation not in {"read", "write", "control_read", "control_write"}:
            raise ValueError("USB operation must be inspect, read, write, control_read or control_write")
        session = options.pop("_session", None)
        owned = session is None
        if session is None:
            dev = self._find_device(core, device)
        else:
            dev = session["device"]
        number = int(intf["interface_number"])
        import usb.util
        claim_needed = operation in {"read", "write"}
        detached = False
        claimed = False
        if owned and claim_needed:
            with self._session_lock:
                if any(key[0] == device.device_id and key[2] == number
                       for key in self._open_interfaces):
                    raise RuntimeError("USB interface already has an open session; pass its session_id to communicate")
        try:
            if owned and claim_needed:
                if options.get("set_configuration") is True:
                    raise RuntimeError("Open a persistent interface session to explicitly switch USB configuration")
                self._ensure_configuration(dev, intf, options)
                try:
                    if dev.is_kernel_driver_active(number):
                        if not options.get("detach_kernel_driver", False):
                            raise RuntimeError("Kernel driver owns this interface; pass detach_kernel_driver=true only if you understand the effect")
                        dev.detach_kernel_driver(number)
                        detached = True
                except (NotImplementedError, AttributeError):
                    pass
                usb.util.claim_interface(dev, number)
                claimed = True
            elif session is not None and session["interface_number"] != number:
                raise ValueError("Session was opened for a different USB interface")
            if session is None and claim_needed:
                dev.set_interface_altsetting(interface=number,
                                             alternate_setting=int(intf.get("alternate_setting", 0)))
            endpoint = self._to_int(options.get("endpoint", 0))
            timeout = int(options.get("timeout_ms", 1000))
            if not 1 <= timeout <= 120_000:
                raise ValueError("timeout_ms must be between 1 and 120000")
            if operation == "control_read":
                length = int(options.get("length", 64))
                if not 1 <= length <= 1_048_576:
                    raise ValueError("USB read length must be between 1 and 1048576")
                result = dev.ctrl_transfer(self._to_int(options["bmRequestType"]), self._to_int(options["bRequest"]),
                    self._to_int(options.get("wValue", 0)), self._to_int(options.get("wIndex", 0)),
                    length, timeout=timeout)
                return {"data_hex": bytes(result).hex()}
            if operation == "control_write":
                result = dev.ctrl_transfer(self._to_int(options["bmRequestType"]), self._to_int(options["bRequest"]),
                    self._to_int(options.get("wValue", 0)), self._to_int(options.get("wIndex", 0)),
                    data or b"", timeout=timeout)
                return {"bytes_written": int(result)}
            if operation == "read":
                if not endpoint:
                    raise ValueError("endpoint is required for USB read")
                descriptor = next((item for item in intf.get("endpoints", [])
                                   if int(item["address"]) == endpoint), None)
                if descriptor is None or descriptor.get("direction") != "in":
                    raise ValueError("endpoint must be an IN endpoint of the selected USB interface")
                length = int(options.get("length", 64))
                if not 1 <= length <= 1_048_576:
                    raise ValueError("USB read length must be between 1 and 1048576")
                result = dev.read(endpoint, length, timeout=timeout)
                return {"data_hex": bytes(result).hex()}
            if operation == "write":
                if not endpoint:
                    raise ValueError("endpoint is required for USB write")
                descriptor = next((item for item in intf.get("endpoints", [])
                                   if int(item["address"]) == endpoint), None)
                if descriptor is None or descriptor.get("direction") != "out":
                    raise ValueError("endpoint must be an OUT endpoint of the selected USB interface")
                return {"bytes_written": int(dev.write(endpoint, data or b"", timeout=timeout))}
            raise ValueError("Unsupported USB operation")
        finally:
            if owned and claimed:
                try:
                    usb.util.release_interface(dev, number)
                except Exception:
                    pass
            if owned and detached:
                try:
                    dev.attach_kernel_driver(number)
                except Exception:
                    pass

    def open_interface(self, device: Device, interface_id: str, **options: Any) -> Any:
        core = self._usb()
        intf = next((item for item in device.interfaces if item.get("id") == interface_id), None)
        if intf is None:
            raise ValueError(f"Unknown USB interface: {interface_id}")
        dev = self._find_device(core, device)
        number = int(intf["interface_number"])
        session_key = (device.device_id, int(intf["configuration"]), number)
        with self._session_lock:
            if any(key[0] == device.device_id and key[2] == number for key in self._open_interfaces):
                raise RuntimeError("This USB interface is already open in a session; reuse that session or close it first")
            if options.get("set_configuration") is True and any(
                key[0] == device.device_id for key in self._open_interfaces
            ):
                raise RuntimeError("Close this device's other USB sessions before switching configuration")
            self._open_interfaces.add(session_key)
            detached = False
            import usb.util
            try:
                self._ensure_configuration(dev, intf, options)
                try:
                    driver_active = dev.is_kernel_driver_active(number)
                except (NotImplementedError, AttributeError):
                    driver_active = False
                if driver_active:
                    if not options.get("detach_kernel_driver", False):
                        raise RuntimeError("Kernel driver owns this interface; pass detach_kernel_driver=true only if you understand the effect")
                    dev.detach_kernel_driver(number)
                    detached = True
                usb.util.claim_interface(dev, number)
                dev.set_interface_altsetting(interface=number,
                                             alternate_setting=int(intf.get("alternate_setting", 0)))
            except Exception:
                try:
                    usb.util.release_interface(dev, number)
                except Exception:
                    pass
                if detached:
                    try:
                        dev.attach_kernel_driver(number)
                    except Exception:
                        pass
                self._open_interfaces.discard(session_key)
                raise
            return {"device": dev, "interface_number": number, "detached": detached,
                    "session_key": session_key}

    def close_interface(self, device: Device, interface_id: str, session: Any) -> None:
        import usb.util
        dev, number = session["device"], session["interface_number"]
        try:
            usb.util.release_interface(dev, number)
        finally:
            if session.get("detached"):
                try:
                    dev.attach_kernel_driver(number)
                except Exception:
                    pass
            with self._session_lock:
                self._open_interfaces.discard(session.get("session_key"))

