import socket
import unittest
from unittest.mock import patch

from universal_device_mcp.adapters.network import NetworkAdapter
from universal_device_mcp.models import Device


class FakeSocket:
    def __init__(self):
        self.sent = []
        self.timeouts = []
        self.closed = False
        self.connected = None

    def settimeout(self, timeout):
        self.timeouts.append(timeout)

    def connect(self, address):
        self.connected = address

    def sendall(self, payload):
        self.sent.append(payload)

    def send(self, payload):
        self.sent.append(payload)
        return len(payload)

    def recv(self, _length):
        return b"ack"

    def close(self):
        self.closed = True


class NetworkAdapterTests(unittest.TestCase):
    def test_generic_tcp_communication_uses_the_open_session(self):
        connection = FakeSocket()
        device = Device("network-test", "network", "local test service", "mdns:test",
                        identity={"protocol": "tcp", "host": "127.0.0.1", "port": 12345})
        adapter = NetworkAdapter()
        with patch("universal_device_mcp.adapters.network.socket.create_connection",
                   return_value=connection) as connect:
            session = adapter.open_interface(device, "tcp", timeout=5)
            adapter.communicate(device, "tcp", "send", b"hello", _session=session, timeout=5)
            response = adapter.communicate(device, "tcp", "communicate", b"again",
                                           _session=session, timeout=5)
            adapter.close_interface(device, "tcp", session)
        self.assertEqual(("127.0.0.1", 12345), connect.call_args.args[0])
        self.assertEqual([b"hello", b"again"], connection.sent)
        self.assertEqual("ack", response["data_text"])
        self.assertTrue(connection.closed)
        self.assertTrue(all(timeout == 5 for timeout in connection.timeouts))

    def test_generic_udp_communication_uses_the_resolved_datagram_endpoint(self):
        connection = FakeSocket()
        device = Device("network-udp-test", "network", "local UDP service", "mdns:udp-test",
                        identity={"protocol": "udp", "host": "127.0.0.1", "port": 54321})
        adapter = NetworkAdapter()
        addresses = [(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "",
                      ("127.0.0.1", 54321))]
        with patch("universal_device_mcp.adapters.network.socket.getaddrinfo",
                   return_value=addresses) as resolve, \
             patch("universal_device_mcp.adapters.network.socket.socket",
                   return_value=connection) as create_socket:
            session = adapter.open_interface(device, "udp", timeout=5)
            response = adapter.communicate(device, "udp", "communicate", b"hello",
                                           _session=session, timeout=5)
            adapter.close_interface(device, "udp", session)
        resolve.assert_called_once_with("127.0.0.1", 54321, type=socket.SOCK_DGRAM)
        create_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.assertEqual([b"hello"], connection.sent)
        self.assertEqual("ack", response["data_text"])
        self.assertEqual(("127.0.0.1", 54321), connection.connected)
        self.assertTrue(connection.closed)


if __name__ == "__main__":
    unittest.main()
