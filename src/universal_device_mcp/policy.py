"""Access policy loading, mode checking, and enforcement.

Extracted from DeviceService to keep security-critical policy logic in a
self-contained, independently testable module.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .models import Device

CRITICAL_OPERATIONS = {
    "flash", "firmware_update", "erase", "wipe", "format", "delete",
    "remove", "factory_reset", "bootloader_unlock", "execute",
}

READ_OPERATIONS = {"read", "receive", "inspect"}

DEFAULT_TRUSTED_OPERATIONS = [
    "open", "read", "receive", "write", "send", "communicate", "control_write",
]

DEFAULT_MAX_WRITE_BYTES = 4096


def load_access_policy() -> dict[str, Any]:
    """Load the local access policy from UDMCP_POLICY and UDMCP_ACCESS_MODE.

    Returns a dict with ``path`` (policy file path or None) and ``policy``
    (normalized policy dict with defaults applied).
    """
    mode = os.environ.get("UDMCP_ACCESS_MODE", "safe").strip().lower()
    if mode not in {"safe", "trusted", "full"}:
        raise ValueError("UDMCP_ACCESS_MODE must be safe, trusted, or full")
    policy_path = os.environ.get("UDMCP_POLICY")
    if not policy_path:
        return {"path": None, "policy": {
            "denied_operations": [], "allowed_operations": [],
            "max_write_bytes": DEFAULT_MAX_WRITE_BYTES, "access_mode": mode}}
    with open(policy_path, encoding="utf-8") as handle:
        policy = json.load(handle)
    if not isinstance(policy, dict):
        raise ValueError("Access policy must be a JSON object")
    policy.setdefault("denied_operations", [])
    policy.setdefault("allowed_operations", [])
    policy.setdefault("max_write_bytes", DEFAULT_MAX_WRITE_BYTES)
    policy["access_mode"] = mode
    return {"path": policy_path, "policy": policy}


def require_media_capture() -> None:
    """Raise PermissionError if media capture is not owner-enabled."""
    if os.environ.get("UDMCP_MEDIA_CAPTURE", "false").lower() not in {"1", "true", "yes"}:
        raise PermissionError(
            "Media capture is disabled; the computer owner must set UDMCP_MEDIA_CAPTURE=true")


def enforce_access_policy(
    device: Device,
    operation: str,
    data: bytes | None,
    interface_id: str | None = None,
) -> None:
    """Enforce the local access policy for a device operation.

    Raises PermissionError if the operation is not permitted, ValueError if
    the policy file is malformed.
    """
    policy = load_access_policy()["policy"]
    operation_lower = operation.lower()
    if operation_lower in CRITICAL_OPERATIONS:
        raise PermissionError(f"Critical operation {operation!r} is blocked in every access mode")

    denied = policy.get("denied_operations", [])
    if not isinstance(denied, list):
        raise ValueError("policy.denied_operations must be a list")
    for rule in denied:
        if not isinstance(rule, dict):
            raise ValueError("Each denied_operations entry must be an object")
        if (rule.get("transport", "*") in ("*", device.transport) and
                rule.get("operation", "*") in ("*", operation) and
                rule.get("device_id", "*") in ("*", device.device_id, device.fingerprint) and
                rule.get("interface_id", "*") in ("*", interface_id)):
            raise PermissionError(f"Blocked by local policy for {device.transport}/{operation}")

    allowed = policy.get("allowed_operations", [])
    if not isinstance(allowed, list):
        raise ValueError("policy.allowed_operations must be a list")
    explicitly_allowed = False
    for rule in allowed:
        if not isinstance(rule, dict):
            raise ValueError("Each allowed_operations entry must be an object")
        explicitly_allowed = explicitly_allowed or (
            rule.get("transport") == device.transport and
            rule.get("device_id") in (device.device_id, device.fingerprint) and
            rule.get("operation") == operation and
            rule.get("interface_id") == interface_id
        )

    mode = policy["access_mode"]
    trusted_devices = policy.get("trusted_devices", [])
    trusted_operations = policy.get("trusted_operations", DEFAULT_TRUSTED_OPERATIONS)
    if not isinstance(trusted_devices, list) or not isinstance(trusted_operations, list):
        raise ValueError("trusted_devices and trusted_operations must be arrays in UDMCP_POLICY")
    trusted_match = device.device_id in trusted_devices or device.fingerprint in trusted_devices
    if mode == "trusted" and operation in trusted_operations and trusted_match:
        explicitly_allowed = True

    if operation not in READ_OPERATIONS and not explicitly_allowed and mode != "full":
        raise PermissionError(
            f"Blocked by {mode} policy for {device.transport}/{operation}; "
            "add an exact transport, device_id, interface_id and operation rule to UDMCP_POLICY"
        )

    max_write = policy.get("max_write_bytes")
    if data is not None and operation not in READ_OPERATIONS and max_write is not None:
        if not isinstance(max_write, int) or max_write < 0:
            raise ValueError("policy.max_write_bytes must be a non-negative integer or null")
        if len(data) > max_write:
            raise PermissionError(f"Payload is {len(data)} bytes; local policy limit is {max_write}")