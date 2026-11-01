from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from typing import Any

from .base import Adapter
from ..models import Device


class ADBAdapter(Adapter):
    transport = "adb"

    _ENDPOINT = re.compile(r"^(?:\[[0-9a-fA-F:]+\]|[A-Za-z0-9._-]+):\d+$")

    def discover(self) -> list[Device]:
        adb = shutil.which("adb")
        if not adb:
            raise RuntimeError("adb executable not found on PATH")
        proc = subprocess.run([adb, "devices", "-l"], capture_output=True, text=True, timeout=10, check=False)
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or "adb devices failed")
        devices = []
        for line in proc.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            fingerprint = f"adb:{serial}"
            attrs = dict(item.split(":", 1) for item in parts[2:] if ":" in item)
            devices.append(Device(device_id=f"adb-{hashlib.sha1(serial.encode()).hexdigest()[:12]}",
                transport=self.transport, name=attrs.get("model", serial), fingerprint=fingerprint,
                identity={"serial": serial, "state": state, "fingerprint_basis": "adb_serial", **attrs}, hardware={},
                interfaces=[{"id": "shell", "kind": "adb-shell"}] if state == "device" else []))
        return devices

    def discover_wireless_services(self) -> list[dict[str, str]]:
        """Read ADB's mDNS service table and return TLS pairing/connect endpoints."""
        adb = shutil.which("adb")
        if not adb:
            raise RuntimeError("adb executable not found on PATH")
        proc = subprocess.run([adb, "mdns", "services"], capture_output=True,
                              text=True, timeout=10, check=False)
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "adb mdns services failed")
        services: list[dict[str, str]] = []
        for line in proc.stdout.splitlines():
            fields = line.split()
            service_type = next((part for part in fields
                                 if "adb-tls-pairing._tcp" in part or "adb-tls-connect._tcp" in part), None)
            endpoint = next((part for part in reversed(fields) if self._ENDPOINT.fullmatch(part)), None)
            if not service_type or not endpoint:
                continue
            kind = "pairing" if "tls-pairing" in service_type else "connect"
            instance = fields[0] if fields and fields[0] != service_type else ""
            services.append({"kind": kind, "service_type": service_type,
                             "instance": instance, "endpoint": endpoint})
        return services

    def pair_wireless(self, endpoint: str, pairing_code: str) -> dict[str, Any]:
        if not re.fullmatch(r"\d{6}", pairing_code):
            raise ValueError("Android Wireless Debugging pairing code must contain six digits")
        services = self.discover_wireless_services()
        if not any(item["kind"] == "pairing" and item["endpoint"] == endpoint for item in services):
            raise ValueError("Pairing endpoint was not advertised by ADB mDNS; refresh wireless discovery")
        adb = shutil.which("adb")
        proc = subprocess.run([adb, "pair", endpoint], input=pairing_code + "\n",
                              capture_output=True, text=True, timeout=30, check=False)
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "adb pair failed")
        return {"endpoint": endpoint, "paired": True,
                "message": proc.stdout.strip() or "Pairing command completed"}

    def connect_wireless(self, endpoint: str) -> dict[str, Any]:
        services = self.discover_wireless_services()
        if not any(item["kind"] == "connect" and item["endpoint"] == endpoint for item in services):
            raise ValueError("Connect endpoint was not advertised by ADB mDNS; refresh wireless discovery")
        adb = shutil.which("adb")
        proc = subprocess.run([adb, "connect", endpoint], capture_output=True,
                              text=True, timeout=20, check=False)
        output = (proc.stdout or proc.stderr).strip()
        if proc.returncode or "unable to connect" in output.lower() or "failed" in output.lower():
            raise RuntimeError(output or "adb connect failed")
        return {"endpoint": endpoint, "connected": True, "message": output}

    def inspect(self, device: Device) -> dict[str, Any]:
        if device.identity.get("state") != "device":
            return {"serial": device.identity["serial"], "state": device.identity.get("state"),
                    "accessible": False, "reason": "Accept the Android debugging prompt or reconnect the device."}
        return {"serial": device.identity["serial"], "properties": self._shell(device, ["getprop"]),
                "mounts": self._shell(device, ["mount"])}

    @staticmethod
    def _shell(device: Device, args: list[str]) -> str:
        adb = shutil.which("adb")
        if not adb:
            raise RuntimeError("adb executable not found on PATH")
        proc = subprocess.run([adb, "-s", device.identity["serial"], "shell", *args],
                              capture_output=True, text=True, timeout=20, check=False)
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or "ADB command failed")
        return proc.stdout

    def communicate(self, device: Device, interface_id: str, operation: str,
                    data: bytes | None = None, **options: Any) -> dict[str, Any]:
        if device.identity.get("state") != "device":
            raise RuntimeError(f"ADB device state is {device.identity.get('state')!r}; shell access is not authorized")
        if interface_id != "shell":
            raise ValueError("ADB interface_id must be 'shell'")
        if operation != "execute":
            raise ValueError("ADB supports inspect or execute; provide an argv array")
        argv = options.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise ValueError("argv must be a non-empty array of strings")
        return {"stdout": self._shell(device, argv)}

