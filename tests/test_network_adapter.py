import socket
import threading
import unittest

from universal_device_mcp.adapters.network import NetworkAdapter
from universal_device_mcp.models import Device


class NetworkAdapterTests(unittest.TestCase):
    def test_generic_udp_communication(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        received = []

        def serve_once():
            payload, peer = listener.recvfrom(64)
            received.append(payload)
            listener.sendto(b"ack", peer)
            listener.close()

        server = threading.Thread(target=serve_once, daemon=True)
        server.start()
        device = Device("network-udp-test", "network", "local UDP service", "mdns:udp-test",
                        identity={"protocol": "udp", "host": "127.0.0.1", "port": port})
        adapter = NetworkAdapter()
        session = adapter.open_interface(device, "udp", timeout=10.0)
        response = adapter.communicate(device, "udp", "communicate", b"hello", _session=session,
                                       timeout=10.0)
        adapter.close_interface(device, "udp", session)
        server.join(timeout=2)
        self.assertEqual([b"hello"], received)
        self.assertEqual("ack", response["data_text"])

    def test_generic_tcp_communication(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        received = []

        def serve_once():
            connection, _ = listener.accept()
            with connection:
                payload = b""
                while len(payload) < 10:
                    payload += connection.recv(32)
                received.append(payload)
                connection.sendall(b"ack")
            listener.close()

        server = threading.Thread(target=serve_once, daemon=True)
        server.start()
        device = Device("network-test", "network", "local test service", "mdns:test",
                        identity={"protocol": "tcp", "host": "127.0.0.1", "port": port})
        adapter = NetworkAdapter()
        session = adapter.open_interface(device, "tcp", timeout=10.0)
        adapter.communicate(device, "tcp", "send", b"hello", _session=session, timeout=10.0)
        response = adapter.communicate(device, "tcp", "communicate", b"again", _session=session,
                                       timeout=10.0)
        adapter.close_interface(device, "tcp", session)
        server.join(timeout=2)
        self.assertEqual([b"helloagain"], received)
        self.assertEqual("ack", response["data_text"])


if __name__ == "__main__":
    unittest.main()
