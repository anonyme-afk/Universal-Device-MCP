"""iPhone and iPad adapter backed by the cross-platform pymobiledevice3 CLI."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from typing import Any, ClassVar

from ..models import Device
from .base import Adapter


class IOSAdapter(Adapter):
    """Discover iOS devices and call pymobiledevice3 commands without a shell.

    iOS has no general-purpose device shell. This adapter forwards a command
    argument vector to pymobiledevice3 and pins it to the selected device UDID.
    Access still depends on Apple's trust, pairing and unlock requirements.
    """

    transport = "ios"
    _MAX_OUTPUT = 2 * 1024 * 1024
    _TARGET_FLAGS: ClassVar[set[str]] = {"--udid", "-u", "--usbmux", "--tunnel", "--rsd", "--mobdev2"}

    @staticmethod
    def _command_prefix() -> list[str]:
        executable = shutil.which("pymobiledevice3")
        if executable:
            return [executable]
        if importlib.util.find_spec("pymobiledevice3"):
            return [sys.executable, "-m", "pymobiledevice3"]
        raise RuntimeError("iOS support requires pymobiledevice3: "
                           "install with pip install universal-device-mcp[ios]")

    @classmethod
    def _run(cls, args: list[str], *, timeout: float = 25) -> str:
        try:
            result = subprocess.run([*cls._command_prefix(), *args], capture_output=True, text=True,
                                    timeout=timeout, check=False, shell=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"pymobiledevice3 timed out after {timeout:g} seconds") from exc
        output = result.stdout or ""
        if len(output.encode("utf-8", errors="replace")) > cls._MAX_OUTPUT:
            raise RuntimeError("pymobiledevice3 output exceeded the 2 MiB response limit")
        if result.returncode:
            message = (result.stderr or output).strip()
            raise RuntimeError(message[-4000:] or f"pymobiledevice3 exited with {result.returncode}")
        return output

    @staticmethod
    def _udids(output: str) -> list[str]:
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            parsed = [line.strip() for line in output.splitlines() if line.strip()]
        if not isinstance(parsed, list):
            raise RuntimeError("Unexpected output from pymobiledevice3 usbmux list --simple")
        values: list[str] = []
        for item in parsed:
            candidate = item if isinstance(item, str) else item.get("udid") if isinstance(item, dict) else None
            if isinstance(candidate, str) and candidate.strip() and candidate not in values:
                values.append(candidate.strip())
        return values

    def discover(self) -> list[Device]:
        errors: list[str] = []
        cli_succeeded = False
        try:
            udids = self._udids(self._run(["usbmux", "list", "--simple"], timeout=15))
            cli_succeeded = True
        except Exception as exc:
            udids = []
            errors.append(str(exc))
        devices: list[Device] = []
        for udid in udids:
            fingerprint = f"ios:{udid}"
            short_id = hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
            devices.append(Device(
                device_id=f"ios-{short_id}", transport=self.transport,
                name=f"Apple iOS device ({udid})", fingerprint=fingerprint,
                identity={"udid": udid, "state": "connected", "fingerprint_basis": "ios_udid",
                          "pairing_status": "unknown; inspect the device to check trust and access"},
                hardware={"vendor_id": "0x05ac"}, interfaces=[
                    {"id": "lockdown", "kind": "ios-lockdown",
                     "description": "Read device information and access paired iOS services"},
                    {"id": "ios-cli", "kind": "pymobiledevice3-cli",
                     "description": "Run a pymobiledevice3 subcommand against this device"},
                ]))
        # A best-effort USB descriptor scan can identify Apple's physical USB
        # device before lockdown pairing is possible. It cannot unlock or bypass
        # Apple's trust/USB Restricted Mode protections.
        try:
            devices.extend(self._discover_usb_descriptors(devices))
        except Exception as exc:
            if not devices and not cli_succeeded:
                errors.append(str(exc))
        if not devices and errors:
            raise RuntimeError("; ".join(dict.fromkeys(errors)))
        return devices

    def _discover_usb_descriptors(self, paired_devices: list[Device]) -> list[Device]:
        """Return visible Apple USB descriptors without depending on lockdown access."""
        import usb.core

        found: list[Device] = []
        paired_fingerprints = {device.fingerprint for device in paired_devices}
        for raw in usb.core.find(find_all=True, idVendor=0x05AC) or []:
            serial = self._usb_string(raw, "serial_number")
            bus = getattr(raw, "bus", None)
            address = getattr(raw, "address", None)
            location = getattr(raw, "port_numbers", None) or f"address-{address}"
            fingerprint = f"ios:{serial}" if serial else f"ios-usb:{bus}:{location}"
            if fingerprint in paired_fingerprints:
                continue
            vid, pid = int(raw.idVendor), int(raw.idProduct)
            stable_id = hashlib.sha256(fingerprint.encode()).hexdigest()[:12]
            interface = {
                "id": "usb-descriptors", "kind": "ios-usb-device",
                "description": "Basic USB descriptors only; lockdown services may require unlock and trust"}
            found.append(Device(
                device_id=f"ios-usb-{stable_id}", transport=self.transport,
                name=self._usb_string(raw, "product") or f"Apple USB device {vid:04x}:{pid:04x}",
                fingerprint=fingerprint,
                identity={"serial": serial, "state": "usb_detected", "bus": bus,
                          "address": address, "fingerprint_basis": "usb_serial_or_port"},
                hardware={"vendor_id": f"0x{vid:04x}", "product_id": f"0x{pid:04x}",
                          "manufacturer": self._usb_string(raw, "manufacturer")},
                interfaces=[interface]))
        return found

    def discover_wireless_services(self) -> list[dict[str, Any]]:
        """Discover Apple mobdev2 Bonjour services for hosts that already paired."""
        output = self._run(["bonjour", "mobdev2"], timeout=20)
        try:
            result = json.loads(output)
        except json.JSONDecodeError:
            return [{"advertisement": line} for line in output.splitlines() if line.strip()]
        if isinstance(result, list):
            return [item if isinstance(item, dict) else {"advertisement": item} for item in result]
        if isinstance(result, dict):
            return [result]
        return []

    @staticmethod
    def _usb_string(device: Any, field: str) -> str | None:
        index_name = {"serial_number": "iSerialNumber", "product": "iProduct",
                      "manufacturer": "iManufacturer"}[field]
        index = int(getattr(device, index_name, 0) or 0)
        if not index:
            return None
        try:
            import usb.util
            return usb.util.get_string(device, index)
        except Exception:
            return None

    def inspect(self, device: Device) -> dict[str, Any]:
        if not device.identity.get("udid"):
            return {"accessible": False, "identity": device.identity, "hardware": device.hardware,
                    "interfaces": device.interfaces,
                    "reason": "Only USB descriptors are available. Unlock the iPhone/iPad, approve Trust "
                              "This Computer, and install the host support required by pymobiledevice3 "
                              "to access lockdown services."}
        output = self._run(["lockdown", "info", "--udid", device.identity["udid"]], timeout=30)
        try:
            info = json.loads(output)
        except json.JSONDecodeError:
            info = {"raw": output[:self._MAX_OUTPUT]}
        if not isinstance(info, dict):
            info = {"items": info}
        return {"udid": device.identity["udid"], "accessible": True,
                "device_info": info, "interfaces": device.interfaces,
                "note": "Fields and services depend on iOS version, trust, unlock state, and pairing."}

    def communicate(self, device: Device, interface_id: str, operation: str,
                    data: bytes | None = None, **options: Any) -> dict[str, Any]:
        if data is not None:
            raise ValueError("iOS CLI commands take argv options; raw bytes are not supported")
        if not device.identity.get("udid"):
            raise RuntimeError("This device is visible only as USB descriptors; unlock and trust it first")
        if interface_id == "lockdown" and operation == "inspect":
            return self.inspect(device)
        if interface_id != "ios-cli" or operation != "execute":
            raise ValueError("iOS supports lockdown inspect or ios-cli execute")
        argv = options.get("argv")
        if not isinstance(argv, list) or not argv or len(argv) > 64 or not all(
                isinstance(arg, str) and "\x00" not in arg and len(arg) <= 4096 for arg in argv):
            raise ValueError("argv must be a non-empty array of at most 64 strings (4096 characters each)")
        if "--" in argv or any(arg.split("=", 1)[0] in self._TARGET_FLAGS for arg in argv):
            raise ValueError("Do not override iOS device/transport selection; adapter pins the UDID")
        output = self._run([*argv, "--udid", device.identity["udid"]], timeout=120)
        try:
            result: Any = json.loads(output)
        except json.JSONDecodeError:
            result = output[:self._MAX_OUTPUT]
        return {"udid": device.identity["udid"], "argv": argv, "result": result,
                "note": "Commands can modify the device; service access depends on trust and device state."}
