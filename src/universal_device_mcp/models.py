"""Shared, transport-neutral device data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Device:
    device_id: str
    transport: str
    name: str
    fingerprint: str
    identity: dict[str, Any] = field(default_factory=dict)
    hardware: dict[str, Any] = field(default_factory=dict)
    interfaces: list[dict[str, Any]] = field(default_factory=list)
    connected: bool = True
    discovered_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

