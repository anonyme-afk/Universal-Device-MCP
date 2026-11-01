from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from .base import Adapter
from ..models import Device


class BluetoothAdapter(Adapter):
    transport = "bluetooth"

    @staticmethod
    def _bleak():
        try:
            from bleak import BleakClient, BleakScanner
        except ImportError as exc:
            raise RuntimeError("Bluetooth support requires: pip install universal-device-mcp[bluetooth]") from exc
        return BleakClient, BleakScanner

    def discover(self) -> list[Device]:
        _, scanner = self._bleak()
        async def scan():
            found = await scanner.discover(timeout=5.0, return_adv=True)
            devices = []
            for address, (item, adv) in found.items():
                fingerprint = f"ble:{address.lower()}"
                devices.append(Device(device_id=f"ble-{hashlib.sha1(fingerprint.encode()).hexdigest()[:12]}",
                    transport=self.transport, name=item.name or adv.local_name or address,
                    fingerprint=fingerprint, identity={"address": address, "rssi": adv.rssi,
                    "local_name": adv.local_name, "fingerprint_basis": "bluetooth_platform_address"},
                    hardware={"advertisement_data": {str(k): bytes(v).hex() for k, v in adv.service_data.items()},
                    "manufacturer_data": {str(k): bytes(v).hex() for k,v in adv.manufacturer_data.items()},
                    "service_uuids": list(adv.service_uuids)}, interfaces=[]))
            return devices
        return asyncio.run(scan())

    def inspect(self, device: Device) -> dict[str, Any]:
        client_cls, _ = self._bleak()
        async def read_services():
            async with client_cls(device.identity["address"]) as client:
                return await self._service_details(client)
        return asyncio.run(read_services())

    @staticmethod
    async def _service_details(client: Any) -> dict[str, Any]:
        # Bleak populates the service collection during connection; get_services()
        # has been deprecated and removed from recent Bleak releases.
        services = client.services
        return {"services": [{"uuid": s.uuid, "description": s.description,
            "characteristics": [{"uuid": c.uuid, "description": c.description,
            "properties": list(c.properties)} for c in s.characteristics]} for s in services]}

    def communicate(self, device: Device, interface_id: str, operation: str,
                    data: bytes | None = None, **options: Any) -> dict[str, Any]:
        client_cls, _ = self._bleak()
        characteristic = options.get("characteristic_uuid") or interface_id
        async def run():
            async with client_cls(device.identity["address"]) as client:
                if operation == "read":
                    value = await client.read_gatt_char(characteristic)
                    return {"data_hex": bytes(value).hex()}
                if operation == "write":
                    await client.write_gatt_char(characteristic, data or b"", response=bool(options.get("response", True)))
                    return {"bytes_written": len(data or b"")}
                if operation == "inspect":
                    return await self._service_details(client)
                raise ValueError("BLE operation must be inspect, read or write")
        return asyncio.run(run())

