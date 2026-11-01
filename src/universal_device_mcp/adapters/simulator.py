"""Deterministic virtual devices for safe installation and multi-target smoke tests."""

from __future__ import annotations

from typing import Any

from ..models import Device
from .base import Adapter


class SimulatorAdapter(Adapter):
    transport = "simulator"

    def discover(self) -> list[Device]:
        return [Device(f"sim-sensor-{index:02d}", self.transport,
                       f"UDMCP simulated sensor {index:02d}", f"simulator:sensor-{index:02d}",
                       identity={"model": "UDMCP-Sensor", "unit": f"{index:02d}"},
                       hardware={"firmware": "demo-1"},
                       interfaces=[{"id": "telemetry", "kind": "simulated-read"}])
                for index in range(1, 11)]

    def communicate(self, device: Device, interface_id: str, operation: str,
                    data: bytes | None = None, **options: Any) -> dict[str, Any]:
        if interface_id != "telemetry":
            raise ValueError(f"Unknown simulated interface: {interface_id}")
        if operation in {"read", "receive"}:
            return {"device": device.identity["unit"], "sample": {"temperature_c": 21.5,
                    "sequence": int(device.identity["unit"])}, "simulated": True}
        if operation in {"write", "send"}:
            return {"accepted_bytes": len(data or b""), "simulated": True}
        raise ValueError(f"Unsupported simulator operation: {operation}")
