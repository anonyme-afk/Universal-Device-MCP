"""Local service discovery and generic TCP/UDP communication over mDNS/DNS-SD."""

from __future__ import annotations

import hashlib
import socket
import threading
from typing import Any

from ..models import Device
from .base import Adapter


class _ServiceTypeListener:
    def __init__(self) -> None:
        self.types: set[str] = set()

    def add_service(self, zeroconf: Any, service_type: str, name: str) -> None:
        self.types.add(name)

    def update_service(self, zeroconf: Any, service_type: str, name: str) -> None:
        self.types.add(name)

    def remove_service(self, zeroconf: Any, service_type: str, name: str) -> None:
        self.types.discard(name)


class _InstanceListener:
    def __init__(self, zeroconf: Any, service_type: str, output: list[Device], lock: threading.Lock) -> None:
        self.zeroconf = zeroconf
        self.service_type = service_type
        self.output = output
        self.lock = lock

    def add_service(self, zeroconf: Any, service_type: str, name: str) -> None:
        info = zeroconf.get_service_info(service_type, name, timeout=500)
        if info is None:
            return
        props = {str(k.decode("utf-8", "replace") if isinstance(k, bytes) else k):
                 (v.hex() if isinstance(v, bytes) else str(v)) for k, v in info.properties.items()}
        addresses = info.parsed_addresses()
        host = addresses[0] if addresses else info.server.rstrip(".")
        transport = "tcp" if "._tcp." in service_type else "udp"
        fingerprint = f"mdns:{service_type}:{name}"
        device = Device(
            device_id=f"network-{hashlib.sha1(fingerprint.encode()).hexdigest()[:12]}",
            transport="network", name=name.removesuffix("."), fingerprint=fingerprint,
            identity={"service_name": name, "service_type": service_type,
                      "host": host, "addresses": addresses, "port": int(info.port),
                      "protocol": transport, "server": info.server,
                      "fingerprint_basis": "mdns_service_instance"},
            hardware={"service_properties": props, "priority": info.priority, "weight": info.weight},
            interfaces=[{"id": transport, "kind": "network", "service_type": service_type,
                         "host": host, "port": int(info.port)}])
        with self.lock:
            if not any(item.fingerprint == fingerprint for item in self.output):
                self.output.append(device)

    def update_service(self, zeroconf: Any, service_type: str, name: str) -> None:
        self.add_service(zeroconf, service_type, name)

    def remove_service(self, zeroconf: Any, service_type: str, name: str) -> None:
        return


class NetworkAdapter(Adapter):
    """Discover advertised local services; communicate only with those services."""

    transport = "network"

    def discover(self) -> list[Device]:
        try:
            from zeroconf import ServiceBrowser, Zeroconf
        except ImportError as exc:
            raise RuntimeError("Local network discovery requires: pip install universal-device-mcp[network]") from exc
        zeroconf = Zeroconf()
        type_listener = _ServiceTypeListener()
        meta_browser = ServiceBrowser(zeroconf, "_services._dns-sd._udp.local.", type_listener)
        try:
            threading.Event().wait(0.5)
            meta_browser.cancel()
            devices: list[Device] = []
            lock = threading.Lock()
            browsers = [ServiceBrowser(zeroconf, service_type, _InstanceListener(zeroconf, service_type, devices, lock))
                        for service_type in sorted(type_listener.types)
                        if "._tcp." in service_type or "._udp." in service_type]
            threading.Event().wait(1.0)
            for browser in browsers:
                browser.cancel()
            return devices
        finally:
            meta_browser.cancel()
            zeroconf.close()

    def communicate(self, device: Device, interface_id: str, operation: str,
                    data: bytes | None = None, **options: Any) -> dict[str, Any]:
        protocol = device.identity.get("protocol")
        if protocol not in {"tcp", "udp"} or interface_id != protocol:
            raise ValueError("Network interface_id must match a discovered TCP or UDP service")
        if operation == "inspect":
            return {"service": device.identity, "properties": device.hardware.get("service_properties", {})}
        if operation not in {"read", "receive", "write", "send", "communicate"}:
            raise ValueError("Network operation must be inspect, read, receive, write, send or communicate")
        timeout = float(options.get("timeout", 2.0))
        if not 0.1 <= timeout <= 60:
            raise ValueError("timeout must be between 0.1 and 60 seconds")
        length = int(options.get("length", 4096))
        if not 1 <= length <= 1_048_576:
            raise ValueError("network read length must be between 1 and 1048576")
        target = (device.identity["host"], int(device.identity["port"]))
        connection = options.pop("_session", None)
        owned = connection is None
        if owned:
            if protocol == "tcp":
                connection = socket.create_connection(target, timeout=timeout)
            else:
                candidates = socket.getaddrinfo(target[0], target[1], type=socket.SOCK_DGRAM)
                family, socktype, proto, _, sockaddr = candidates[0]
                connection = socket.socket(family, socktype, proto)
                try:
                    connection.settimeout(timeout)
                    connection.connect(sockaddr)
                except Exception:
                    connection.close()
                    raise
        try:
            connection.settimeout(timeout)
            if operation in {"write", "send", "communicate"}:
                if protocol == "tcp":
                    connection.sendall(data or b"")
                else:
                    connection.send(data or b"")
                if operation in {"write", "send"}:
                    return {"bytes_written": len(data or b"")}
            payload = connection.recv(length)
            return {"data_hex": payload.hex(), "data_text": payload.decode("utf-8", errors="replace")}
        finally:
            if owned:
                connection.close()

    def open_interface(self, device: Device, interface_id: str, **options: Any) -> Any:
        protocol = device.identity.get("protocol")
        if protocol not in {"tcp", "udp"} or interface_id != protocol:
            raise ValueError("Only discovered TCP or UDP service interfaces can be opened")
        timeout = float(options.get("timeout", 2.0))
        if not 0.1 <= timeout <= 60:
            raise ValueError("timeout must be between 0.1 and 60 seconds")
        target = (device.identity["host"], int(device.identity["port"]))
        if protocol == "tcp":
            return socket.create_connection(target, timeout=timeout)
        candidates = socket.getaddrinfo(target[0], target[1], type=socket.SOCK_DGRAM)
        family, socktype, proto, _, sockaddr = candidates[0]
        connection = socket.socket(family, socktype, proto)
        try:
            connection.settimeout(timeout)
            connection.connect(sockaddr)
            return connection
        except Exception:
            connection.close()
            raise

