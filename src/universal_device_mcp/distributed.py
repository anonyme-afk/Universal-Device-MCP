"""Authenticated, read-only V2 hub connections to separately running UDMCP nodes."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings


@dataclass(frozen=True)
class RemoteNode:
    node_id: str
    url: str
    token_env: str
    organization_id: str = "default"
    site: str = "default"

    def token(self) -> str:
        value = os.environ.get(self.token_env, "")
        if len(value) < 32:
            raise ValueError(f"Remote node {self.node_id!r} needs a 32-character token in {self.token_env}")
        return value


class RemoteNodeRegistry:
    """Load fixed hub targets from JSON; tool callers cannot supply arbitrary URLs."""

    def __init__(self, nodes: list[RemoteNode] | None = None) -> None:
        self.nodes = nodes if nodes is not None else self._load()
        ids = [node.node_id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("UDMCP_REMOTE_NODES contains duplicate node_id values")

    @staticmethod
    def _load() -> list[RemoteNode]:
        raw = os.environ.get("UDMCP_REMOTE_NODES", "[]")
        try:
            items = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("UDMCP_REMOTE_NODES must be a JSON array") from exc
        if not isinstance(items, list) or len(items) > 128:
            raise ValueError("UDMCP_REMOTE_NODES must be an array with at most 128 nodes")
        nodes = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Each remote node definition must be an object")
            node_id, url, token_env = item.get("node_id"), item.get("url"), item.get("token_env")
            if not all(isinstance(value, str) and value.strip() for value in (node_id, url, token_env)):
                raise ValueError("Each remote node requires non-empty node_id, url and token_env strings")
            parsed = urlsplit(url)
            if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError(f"Remote node {node_id!r} needs an HTTP(S) URL without credentials")
            if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError(f"Remote node {node_id!r} must use HTTPS outside loopback")
            if parsed.query or parsed.fragment:
                raise ValueError(f"Remote node {node_id!r} URL cannot contain a query or fragment")
            nodes.append(RemoteNode(node_id.strip(), url.rstrip("/"), token_env.strip(),
                                    str(item.get("organization_id", "default")),
                                    str(item.get("site", "default"))))
        return nodes

    def get(self, node_id: str) -> RemoteNode:
        node = next((item for item in self.nodes if item.node_id == node_id), None)
        if node is None:
            raise KeyError(f"Unknown remote node {node_id!r}; use list_remote_nodes")
        return node

    def list(self) -> list[dict[str, str]]:
        return [{"node_id": node.node_id, "organization_id": node.organization_id,
                 "site": node.site, "url": node.url, "transport": "streamable-http"}
                for node in self.nodes]

    async def call(self, node_id: str, tool: str, arguments: dict[str, Any] | None = None) -> Any:
        node = self.get(node_id)
        headers = {"Authorization": f"Bearer {node.token()}"}
        timeout = httpx2.Timeout(35.0, connect=8.0)
        async with httpx2.AsyncClient(headers=headers, timeout=timeout) as http_client:
            async with streamable_http_client(node.url, http_client=http_client) as streams:
                async with Client(streams, read_timeout_seconds=35) as client:
                    result = await client.call_tool(tool, arguments or {})
        if result.is_error:
            messages = [getattr(item, "text", "") for item in result.content or []]
            raise RuntimeError("; ".join(message for message in messages if message) or
                               f"Remote node {node_id!r} rejected {tool}")
        structured = getattr(result, "structuredContent", None)
        if structured is None:
            structured = getattr(result, "structured_content", None)
        if structured is not None:
            return structured
        return {"content": [getattr(item, "text", str(item)) for item in result.content or []]}

    async def inventory(self) -> dict[str, Any]:
        semaphore = asyncio.Semaphore(8)

        async def scan(node: RemoteNode) -> dict[str, Any]:
            async with semaphore:
                try:
                    result = await self.call(node.node_id, "discover_devices")
                    devices = result.get("devices", []) if isinstance(result, dict) else []
                    return {"node_id": node.node_id, "organization_id": node.organization_id,
                            "site": node.site, "ok": True,
                            "devices": [{**device, "node_id": node.node_id,
                                         "organization_id": node.organization_id, "site": node.site}
                                        for device in devices]}
                except Exception as exc:
                    return {"node_id": node.node_id, "organization_id": node.organization_id,
                            "site": node.site, "ok": False, "error": str(exc), "devices": []}

        results = await asyncio.gather(*(scan(node) for node in self.nodes))
        devices = [device for result in results for device in result["devices"]]
        return {"nodes": results, "node_count": len(results), "online_nodes": sum(r["ok"] for r in results),
                "device_count": len(devices), "devices": devices}

    async def read_many(self, targets: list[dict[str, str]], operation: str = "read") -> dict[str, Any]:
        if operation not in {"read", "receive"}:
            raise ValueError("Remote multi-node batches only allow read or receive")
        if not isinstance(targets, list) or not targets or len(targets) > 32:
            raise ValueError("targets must contain between 1 and 32 exact node/device/interface targets")
        normalized = []
        seen = set()
        for target in targets:
            if not isinstance(target, dict) or not all(
                    isinstance(target.get(key), str) and target[key]
                    for key in ("node_id", "device_id", "interface_id")):
                raise ValueError("Each target requires node_id, device_id and interface_id")
            self.get(target["node_id"])
            key = (target["node_id"], target["device_id"], target["interface_id"])
            if key in seen:
                raise ValueError(f"Duplicate remote target {key}")
            seen.add(key)
            normalized.append({"node_id": key[0], "device_id": key[1], "interface_id": key[2]})
        semaphore = asyncio.Semaphore(16)

        async def read(target: dict[str, str]) -> dict[str, Any]:
            async with semaphore:
                try:
                    response = await self.call(target["node_id"], "communicate", {
                        "device_id": target["device_id"], "interface_id": target["interface_id"],
                        "operation": operation})
                    return {**target, "ok": True, "response": response}
                except Exception as exc:
                    return {**target, "ok": False, "error": str(exc)}

        outcomes = await asyncio.gather(*(read(target) for target in normalized))
        return {"operation": operation, "requested": len(outcomes),
                "completed": sum(outcome["ok"] for outcome in outcomes), "results": outcomes}


class EnvironmentTokenVerifier:
    """Constant-time verifier for one per-node secret supplied outside configuration files."""

    def __init__(self, expected_token: str, resource: str, scopes: list[str]) -> None:
        self._expected = hashlib.sha256(expected_token.encode()).digest()
        self._resource = resource
        self._scopes = scopes

    async def verify_token(self, token: str) -> Any:
        if not hmac.compare_digest(hashlib.sha256(token.encode()).digest(), self._expected):
            return None
        return AccessToken(token=token, client_id="udmcp-hub", scopes=self._scopes,
                           resource=self._resource, subject="configured-remote-hub")


def node_auth_from_environment() -> tuple[Any, Any] | tuple[None, None]:
    """Return SDK bearer authentication for HTTP node mode, or no auth for local stdio."""
    if os.environ.get("UDMCP_ROLE", "standalone").lower() != "node":
        return None, None
    token = os.environ.get("UDMCP_NODE_TOKEN", "")
    resource = os.environ.get("UDMCP_RESOURCE_URL", "")
    if len(token) < 32 or not resource.startswith("https://"):
        raise RuntimeError("Node mode requires UDMCP_NODE_TOKEN (32+ characters) and an HTTPS UDMCP_RESOURCE_URL")
    scopes = [scope for scope in os.environ.get("UDMCP_NODE_SCOPES", "udmcp:read").split(",") if scope]
    verifier = EnvironmentTokenVerifier(token, resource, scopes)
    settings = AuthSettings(issuer_url="https://udmcp.invalid", resource_server_url=resource,
                           required_scopes=["udmcp:read"], validate_token_resource=True)
    return verifier, settings
