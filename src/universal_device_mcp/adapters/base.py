from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import Device


class Adapter(ABC):
    transport: str

    @abstractmethod
    def discover(self) -> list[Device]: ...

    @abstractmethod
    def communicate(self, device: Device, interface_id: str, operation: str,
                    data: bytes | None = None, **options: Any) -> dict[str, Any]: ...

    def inspect(self, device: Device) -> dict[str, Any]:
        return device.to_dict()

    def open_interface(self, device: Device, interface_id: str, **options: Any) -> Any:
        raise NotImplementedError(f"{self.transport} adapter does not support persistent interface sessions")

    def close_interface(self, device: Device, interface_id: str, session: Any) -> None:
        close = getattr(session, "close", None)
        if callable(close):
            close()

