"""Tests for hub configuration and bounded remote read behavior."""

import asyncio

import pytest

from universal_device_mcp.distributed import RemoteNode, RemoteNodeRegistry


def test_registry_rejects_duplicate_node_ids():
    node = RemoteNode("lab", "https://example.test/mcp", "TOKEN")
    with pytest.raises(ValueError, match="duplicate"):
        RemoteNodeRegistry([node, node])


def test_registry_rejects_insecure_non_loopback_http(monkeypatch):
    monkeypatch.setenv("UDMCP_REMOTE_NODES", '[{"node_id":"lab","url":"http://example.test/mcp","token_env":"TOKEN"}]')
    with pytest.raises(ValueError, match="HTTPS"):
        RemoteNodeRegistry()


def test_read_many_keeps_individual_failures(monkeypatch):
    registry = RemoteNodeRegistry([
        RemoteNode("a", "https://a.example/mcp", "TOKEN_A"),
        RemoteNode("b", "https://b.example/mcp", "TOKEN_B"),
    ])

    async def call(node_id, tool, arguments):
        if node_id == "b":
            raise RuntimeError("temporarily offline")
        return {"bytes_read": 2}

    monkeypatch.setattr(registry, "call", call)
    monkeypatch.setenv("TOKEN_A", "a" * 32)
    monkeypatch.setenv("TOKEN_B", "b" * 32)
    targets = [
        {"node_id": "a", "device_id": "usb-1", "interface_id": "bulk-in"},
        {"node_id": "b", "device_id": "usb-1", "interface_id": "bulk-in"},
    ]
    result = asyncio.run(registry.read_many(targets))
    assert result["requested"] == 2
    assert result["completed"] == 1
    assert result["results"][0]["response"] == {"bytes_read": 2}
    assert result["results"][1]["error"] == "temporarily offline"


def test_read_many_rejects_write_and_duplicate_targets():
    registry = RemoteNodeRegistry([RemoteNode("a", "https://a.example/mcp", "TOKEN")])
    target = {"node_id": "a", "device_id": "d", "interface_id": "i"}
    with pytest.raises(ValueError, match="only allow read"):
        asyncio.run(registry.read_many([target], "write"))
    with pytest.raises(ValueError, match="Duplicate"):
        asyncio.run(registry.read_many([target, target]))
