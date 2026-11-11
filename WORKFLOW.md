# Universal Device MCP — AI Agent Workflow

This document is a reusable instruction layer between an AI agent and the **Universal Device MCP** server. It is independent of any platform (Claude, OpenAI, etc.) and does not depend on any specific marketplace.

## Objective

Enable an AI agent to:
1. Discover hardware connected to the host computer.
2. Inspect interfaces and capabilities of each device.
3. Execute operations securely, respecting local access policies.
4. Verify that operations succeeded.
5. Handle errors, unavailable devices, and unsupported operations.

## When to use Universal Device MCP

Use this server when you need to:
- Discover local hardware (USB, serial, Bluetooth, mDNS network, Android ADB, iOS).
- Read or write on hardware interfaces generically.
- Maintain a persistent inventory of discovered devices across sessions.
- Execute operations on multiple devices simultaneously (independent reads).
- Control simulated devices for testing without physical hardware.
- Interact with remote MCP nodes (hub/node mode).

**Do not use this server for:**
- Controlling hardware whose protocol is unknown and undocumented (the server does not guess proprietary formats).
- Accessing hardware without operating system permissions (Windows, macOS, Linux remain authoritative).
- In `unrestricted` mode, performing destructive operations without obtaining an explicit one-time approval via `authorize_destructive_operation` — the AI cannot grant this approval to itself.

## 1. Device Discovery

### Step 1 — Check server status

Before any discovery, verify that the server is running and adapters are available.

**Tool:** `get_runtime_status()`

What you get:
- Python version and OS platform.
- Status of each adapter (USB, HID, Serial, Bluetooth, Network, iOS, ADB).
- Local database path.
- Plugin load errors if any.

### Step 2 — Discover local devices

**Tool:** `discover_devices(transports?)`

Optional parameter `transports`: array of strings (e.g. `["usb"]`, `["bluetooth"]`, `["serial"]`). Supported transports: usb, hid, serial, bluetooth, adb, ios, network, simulator.

Result: a list of devices with `device_id`, `transport`, `name`, `fingerprint`, and detected interfaces.

### Step 3 — Discover wireless and network devices

**Tool:** `discover_wireless_devices()`

Covers BLE peripherals, local mDNS services, wireless Android ADB endpoints, and iOS devices.

### Step 4 — List remembered devices

**Tool:** `list_known_devices()`

Lists devices saved in the local SQLite knowledge database. No parameters.

## 2. Device Capability Inspection

### Step 1 — Inspect a specific device

**Tool:** `inspect_device(device_id)`

Requires an exact `device_id` obtained from discovery.

Result: full profile with interfaces, connection state, and metadata.

### Step 2 — Understand an interface

**Tool:** `explain_device_interface(device_id, interface_id)`

Provides a readable description of what an interface does without claiming its protocol is understood.

### Step 3 — View global capabilities

**Tool:** `get_device_capabilities(device_id)`

Summary of observed interfaces and saved protocol discoveries with their confidence labels.

### Step 4 — View supported protocols

**Tool:** `get_supported_protocols()`

Lists available transport implementations and their adapter classes.

## 3. Selecting the Right MCP Tool

Use this table to choose the appropriate tool for your task:

| Objective | MCP Tool | Read / Write |
|-----------|----------|--------------|
| Discover local hardware | `discover_devices` | Read |
| Discover wireless hardware | `discover_wireless_devices` | Read |
| List remembered devices | `list_known_devices` | Read |
| Check server status | `get_runtime_status` | Read |
| Inspect a device | `inspect_device` | Read |
| Understand an interface | `explain_device_interface` | Read |
| Device capabilities summary | `get_device_capabilities` | Read |
| List supported protocols | `get_supported_protocols` | Read |
| Generic communication | `communicate_device` | Read or Write |
| Concurrent reads | `communicate_many` | Read |
| Open persistent session | `open_interface` | Write (session) |
| Close persistent session | `close_interface` | Write (session) |
| Read device events | `get_device_events` | Read |
| View access policy | `get_access_policy` | Read |
| Reload access policy | `reload_access_policy` | Read |
| Connect device | `connect_device` | Write (state) |
| Disconnect device | `disconnect_device` | Write (state) |
| Delete experiment record | `delete_device_experiment` | Write (history) |
| Camera: discover | `discover_cameras` | Read |
| Camera: capture image | `capture_camera_image` | Write (in-memory) |
| Microphone: discover | `discover_microphones` | Read |
| Microphone: record sample | `record_audio_sample` | Write (in-memory) |
| Device group: create | `create_device_group` | Write (memory) |
| Device group: read | `read_device_group` | Read |
| Device group: prepare write | `prepare_group_write` | Write (plan) |
| Device group: execute write | `execute_approved_group_write` | Write (requires human approval) |
| Device group: delete | `delete_device_group` | Write (memory) |
| Remember discovery | `remember_discovery` | Write (database) |
| Update device profile | `update_device_profile` | Write (database) |
| View device knowledge | `get_device_knowledge` | Read |
| Export device profile | `export_device_profile` | Read |
| Forget device | `forget_device` | Write (deletion) |
| Analyze binary payload | `analyze_payload` | Read |
| Generate device report | `generate_device_report` | Read |
| Run device diagnostics | `run_device_diagnostics` | Read |
| Start connection monitor | `start_device_monitor(interval_seconds?)` | Write (monitoring) |
| Stop connection monitor | `stop_device_monitor()` | Write (monitoring) |
| Remote node: list | `list_remote_nodes()` | Read |
| Remote node: discover | `discover_remote_devices()` | Read |
| Remote node: read | `read_remote_devices(targets, operation?)` | Read |
| Android Wi-Fi: pair | `pair_android_over_wifi(endpoint, pairing_code)` | Write |
| Android Wi-Fi: connect | `connect_android_over_wifi(endpoint)` | Write |
| Authorize destructive operation | `authorize_destructive_operation(device_id, operation, interface_id?, data_hex?)` | Write (security) |
| Revoke destructive approval | `discard_destructive_approval(approval_id)` | Write (security) |
| Confirm unrestricted mode | `confirm_unrestricted_mode()` | Read (security) |

## 4. Secure Operation Execution

### Golden Rule: Never assume

Before executing any write operation:
1. Verify the device exists and is currently connected (`inspect_device`, field `connected`).
2. Verify the interface exists (`interfaces` in inspection output).
3. Check the access policy (`get_access_policy`) to determine current mode (`safe`, `trusted`, `full`, `unrestricted`) and allowed rules.
4. Read interface semantics (`explain_device_interface`).

### Access Modes

The access mode is set locally by the computer owner via the `UDMCP_ACCESS_MODE` environment variable. An AI agent **cannot modify it**.

| Mode | Behavior |
|------|----------|
| `safe` (default) | Reads allowed. Writes blocked unless covered by an exact rule (transport, device_id, interface_id, operation). |
| `trusted` | Reads always allowed. Writes/opens allowed if device is in `trusted_devices` AND operation is in `trusted_operations` (default: open, read, receive, write, send, communicate, control_write), or if an exact `allowed_operations` rule matches. |
| `full` | Non-critical operations permitted without per-operation rules, but size limits, explicit denies, auditing, and critical operation blocks remain enforced. |
| `unrestricted` | All operations (including `flash`, `firmware_update`, `erase`, `wipe`, `format`, `delete`, `remove`, `factory_reset`, `bootloader_unlock`, `execute`) are no longer blocked by default. **However**, each destructive operation requires an explicit one-time human approval via `authorize_destructive_operation` (the AI cannot grant this approval to itself). Explicit denies (`denied_operations`) and payload size limits still apply. |

## MCP Resources

The server exposes two MCP resources (read-only, accessed via `read_resource`):

| Resource | Description |
|----------|-------------|
| `udmcp://devices` | Local inventory of known devices and saved technical profiles (JSON). |
| `udmcp://devices/{device_id}/profile` | Detailed device profile, findings, experiments, and history (JSON). |

## Environment Variables Configuration

| Variable | Values | Description |
|----------|--------|-------------|
| `UDMCP_ACCESS_MODE` | `safe` (default), `trusted`, `full`, `unrestricted` | Access mode selected by the local computer owner. |
| `UDMCP_POLICY` | JSON file path | Path to local policy configuration file. |
| `UDMCP_DATABASE` | File path | Path to SQLite device profile database. |
| `UDMCP_MEDIA_CAPTURE` | `true` (opt-in) | Enables camera and microphone tools. Required for `discover_cameras`, `capture_camera_image`, `discover_microphones`, `record_audio_sample`. |
| `UDMCP_AUTO_MONITOR` | `false` (default), `true` | Automatically starts background connection monitoring on launch. |
| `UDMCP_STORE_PAYLOADS` | `false` (default), `true` | Retains raw payloads of experiments in local database. |
| `UDMCP_RETENTION_DAYS` | Integer (default: 30) | Event log retention period in days. |
| `UDMCP_ROLE` | `standalone` (default), `node`, `hub` | Server role in distributed multi-node setups. |
| `UDMCP_TRANSPORT` | `stdio` (default), `streamable-http` | MCP communication transport. |
| `UDMCP_HTTP_HOST` | `127.0.0.1` (default) | Host for HTTP transport. |
| `UDMCP_HTTP_PORT` | `8000` (default) | Port for HTTP transport. |
| `UDMCP_UNRESTRICTED_CONFIRMED` | `true`, `false` | Explicit owner confirmation required for unrestricted mode. |
| `UDMCP_UNRESTRICTED_BYPASS_APPROVAL` | `true`, `false` | Owner opt-out for per-operation destructive approval in unrestricted mode. |

### Policy File Format (UDMCP_POLICY)

```json
{
  "denied_operations": [
    { "transport": "usb", "operation": "write", "device_id": "*", "interface_id": "*" }
  ],
  "allowed_operations": [
    { "transport": "usb", "device_id": "usb:1", "interface_id": "bulk-out", "operation": "write" }
  ],
  "trusted_devices": ["usb:1", "fingerprint:abc123"],
  "trusted_operations": ["open", "read", "receive", "write", "send", "communicate", "control_write"],
  "max_write_bytes": 4096
}
```

Rules support `*` as a wildcard for transport, operation, device_id, and interface_id.

### Critical Operations and Unrestricted Mode

In `safe`, `trusted`, and `full` modes, the following operations are always blocked:
- `flash`, `firmware_update`, `erase`, `wipe`, `format`, `delete`, `remove`, `factory_reset`, `bootloader_unlock`, `execute`.

In `unrestricted` mode, these operations are no longer blocked by default, but each requires an **explicit one-time approval** via `authorize_destructive_operation` before execution. Approvals expire after 120 seconds and are consumed on first use. The AI cannot grant this approval to itself.

Explicit denial rules (`denied_operations`) in `UDMCP_POLICY` apply across **all** modes, including `unrestricted`, because they represent an express decision by the device owner. Size limits (`max_write_bytes`) also apply in all modes.

### Size Limits

- Single write: `max_write_bytes` (default 4096 bytes, configurable in policy).
- Group write: Maximum 32 targets, 4096 bytes per target.

### Explicit Confirmation for Group Writes

`prepare_group_write` creates a frozen execution plan. `execute_approved_group_write` requires human approval via MCP elicitation. An AI agent cannot execute a group write without explicit human authorization.

### Media Captures (Camera / Microphone)

Requires `UDMCP_MEDIA_CAPTURE=true` (owner opt-in). Nothing is activated automatically. Captures remain strictly in memory and are never persisted to disk.

## 5. Verifying Operation Success

After each tool call:

1. Check that the result does not contain an error (`error` field or exception).
2. For writes: verify `success: true` or equivalent tool-specific acknowledgment.
3. For reads: verify that returned payload data matches the request.
4. For group operations: inspect results per target (each target has its own status; partial failures can occur).
5. Never state an operation succeeded without explicit proof in the tool's response payload.

## 6. Error Handling

### Common Error Types

| Situation | Probable Cause | Action |
|-----------|----------------|--------|
| `KeyError: Unknown device` | Missing `device_id` or forgotten device | Re-run `discover_devices` |
| `PermissionError` | Safe mode policy restriction or restricted operation | Ask owner to adjust local policy |
| `RuntimeError: not currently connected` | Device disconnected | Call `connect_device` first |
| `TimeoutError` | Hardware bus operation stalled | Retry with shorter timeout or abort |
| `ImportError` | Missing optional dependency (e.g. `usb`, `hid`) | Install corresponding package extra |
| `ValueError` | Invalid parameter (e.g. audio duration out of range) | Correct arguments according to tool documentation |

### Unavailable Device

If a device does not respond:
1. Check its connection status (`inspect_device`).
2. Try `disconnect_device` followed by `connect_device`.
3. If the physical cable was disconnected, re-run `discover_devices`.
4. Never assume a disconnected device is permanently gone without re-running discovery.

## 7. Communicating Results to the User

- Clearly report `device_id`, `transport`, and `name` for each device involved.
- Clearly distinguish between successes and failures per target (especially for `communicate_many` and groups).
- Indicate when an operation was blocked by access policy.
- Never invent device properties or behaviors. If an attribute was not returned by the server, report it as unknown.
- For media captures: specify that media is in-memory only, non-persistent, and provide MIME format details.

## Known Limitations

- The server is a generic access layer, not a guarantee that all hardware is controllable.
- Undocumented proprietary protocols remain experiments until validated.
- In `safe`, `trusted`, and `full` modes, the following operations are always blocked: `flash`, `firmware_update`, `erase`, `wipe`, `format`, `delete`, `remove`, `factory_reset`, `bootloader_unlock`, `execute`.
- In `unrestricted` mode, these operations are no longer blocked by default but require a one-time explicit approval via `authorize_destructive_operation`.
- The AI cannot change the access mode (`safe`/`trusted`/`full`/`unrestricted`) — reserved for the local owner.
- Camera/audio captures are limited (one JPEG ≤ 900 KB, ≤ 10 s of mono 16 kHz WAV, no continuous streams).
- Group writes require explicit human approval via MCP elicitation.
- The `denied_operations` rules in `UDMCP_POLICY` apply in all modes, including `unrestricted`.
- The `UDMCP_UNRESTRICTED_CONFIRMED` and `UDMCP_UNRESTRICTED_BYPASS_APPROVAL` environment variables must be set by the computer owner; the AI cannot set them.
- The `confirm_unrestricted_mode()` tool only reports the current state; it does not set the confirmation itself.
