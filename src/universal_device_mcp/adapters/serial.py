from __future__ import annotations

import hashlib
import threading
from typing import Any

from .base import Adapter
from ..models import Device


class SerialAdapter(Adapter):
    transport = "serial"

    def __init__(self) -> None:
        self._session_lock = threading.Lock()
        self._open_ports: set[str] = set()

    @staticmethod
    def _serial_options(options: dict[str, Any]) -> dict[str, Any]:
        timeout = float(options.get("timeout", 1))
        write_timeout = float(options.get("write_timeout", timeout))
        if not 0 <= timeout <= 120:
            raise ValueError("timeout must be between 0 and 120 seconds")
        if not 0 <= write_timeout <= 120:
            raise ValueError("write_timeout must be between 0 and 120 seconds")
        return {"baudrate": int(options.get("baudrate", 9600)), "timeout": timeout,
                "write_timeout": write_timeout,
                "bytesize": int(options.get("bytesize", 8)),
                "parity": str(options.get("parity", "N")).upper(),
                "stopbits": float(options.get("stopbits", 1)),
                "xonxoff": bool(options.get("xonxoff", False)),
                "rtscts": bool(options.get("rtscts", False)),
                "dsrdtr": bool(options.get("dsrdtr", False))}

    def _serial(self):
        try:
            import serial
            from serial.tools import list_ports
        except ImportError as exc:
            raise RuntimeError("Serial support requires: pip install universal-device-mcp[serial]") from exc
        return serial, list_ports

    def discover(self) -> list[Device]:
        _, ports = self._serial()
        result = []
        for port in ports.comports():
            location = getattr(port, "location", None)
            fingerprint = f"serial:{port.vid}:{port.pid}:{port.serial_number or location or port.device}"
            label = port.description or port.device
            result.append(Device(device_id=f"serial-{hashlib.sha1(fingerprint.encode()).hexdigest()[:12]}",
                transport=self.transport, name=label, fingerprint=fingerprint,
                identity={"port": port.device, "vendor_id": port.vid, "product_id": port.pid,
                          "serial_number": port.serial_number, "manufacturer": port.manufacturer,
                          "product": port.product, "interface": port.interface, "location": location,
                          "fingerprint_basis": "vendor_product_serial" if port.serial_number else
                                               ("vendor_product_topology" if location else "host_port")},
                hardware={"description": port.description, "hwid": port.hwid, "location": location},
                interfaces=[{"id": port.device, "kind": "serial", "device": port.device}]))
        return result

    def communicate(self, device: Device, interface_id: str, operation: str,
                    data: bytes | None = None, **options: Any) -> dict[str, Any]:
        serial, _ = self._serial()
        port = device.identity["port"]
        if interface_id != port:
            raise ValueError("interface_id does not match this device's serial port")
        if operation == "inspect":
            return {"port": port, "baudrate": int(options.get("baudrate", 9600))}
        if operation not in {"read", "write", "send", "receive"}:
            raise ValueError("Serial operation must be inspect, read, write, send or receive")
        conn = options.pop("_session", None)
        owned = conn is None
        serial_options = self._serial_options(options)
        length = int(options.get("length", 64))
        if not 1 <= length <= 1_048_576:
            raise ValueError("serial read length must be between 1 and 1048576")
        if owned:
            with self._session_lock:
                if port in self._open_ports:
                    raise RuntimeError("Serial port already has an open session; pass its session_id to communicate")
                self._open_ports.add(port)
            try:
                conn = serial.Serial(port, **serial_options)
            except Exception:
                with self._session_lock:
                    self._open_ports.discard(port)
                raise
        try:
            if operation in {"write", "send"}:
                return {"bytes_written": conn.write(data or b"")}
            payload = conn.read(length)
            return {"data_hex": payload.hex(), "data_text": payload.decode("utf-8", errors="replace")}
        finally:
            if owned:
                try:
                    conn.close()
                finally:
                    with self._session_lock:
                        self._open_ports.discard(port)

    def open_interface(self, device: Device, interface_id: str, **options: Any) -> Any:
        serial, _ = self._serial()
        port = device.identity["port"]
        if interface_id != port:
            raise ValueError("interface_id does not match this device's serial port")
        with self._session_lock:
            if port in self._open_ports:
                raise RuntimeError("Serial port already has an open session")
            self._open_ports.add(port)
        try:
            return serial.Serial(port, **self._serial_options(options))
        except Exception:
            with self._session_lock:
                self._open_ports.discard(port)
            raise

    def close_interface(self, device: Device, interface_id: str, session: Any) -> None:
        port = device.identity["port"]
        try:
            session.close()
        finally:
            with self._session_lock:
                self._open_ports.discard(port)

