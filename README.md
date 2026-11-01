# Universal Device MCP

**Universal Hardware Discovery & Control Platform** — a local-first MCP server that lets an AI agent discover connected hardware, inspect the interfaces exposed by the host operating system, communicate through generic transport operations, and retain per-device knowledge between connections.

> This project is an extensible hardware access layer, not a promise that every device or proprietary protocol can be controlled. Hardware access depends on operating-system permissions, drivers, device state, and available documentation. Unknown command formats remain experiments until validated.

## What works today

- MCP server using the official Python MCP SDK v2 on Python 3.11+. There is no handwritten protocol fallback; installations fail clearly if the supported SDK is missing.
- Structured JSON tool results, with read-only/destructive behavior hints where the action is unambiguous.
- MCP resources for the remembered device inventory and per-device profile/knowledge snapshots.
- Runtime diagnostics through `get_runtime_status`, showing Python/OS, MCP runtime, adapter dependencies, ADB availability, database path and plugin load errors without scanning hardware.
- USB enumeration and descriptor/interface/endpoint inspection through PyUSB.
- Generic USB bulk/interrupt endpoint reads and writes and USB control transfers.
- USB HID device enumeration and generic input/output report access through hidapi.
- Serial port enumeration, inspection, reads and writes through PySerial.
- BLE scan, GATT service/characteristic inspection, reads and writes through Bleak.
- mDNS/DNS-SD discovery of advertised local TCP and UDP services with generic stream/datagram communication.
- Android device discovery, property inspection and generic ADB shell argv execution.
- Android Wireless Debugging discovery, pairing-code pairing and TLS ADB connection through advertised mDNS services.
- iPhone/iPad USB discovery through Apple usbmux, best-effort USB descriptor detection when lockdown access is unavailable, iOS device-info inspection, paired-device Bonjour discovery, and generic `pymobiledevice3` CLI execution pinned to the selected device.
- Local SQLite device profiles, persistent discoveries and configurable, minimized communication history.
- Concurrent adapter discovery and `communicate_many` for independent concurrent reads across explicitly named device/interface targets. Every target has a separate result; batch writes are rejected.
- Persistent selector-based device groups, concurrent per-member reads, and bounded group-write plans that require exact local allow rules plus MCP client elicitation before one-time execution.
- Optional ten-device simulator for installation checks and repeatable multi-device demonstrations.
- Background device monitoring is off by default and can be started explicitly.
- Configuration snapshots that preserve previous hardware/interface layouts when an observed configuration changes.
- Default-deny access for writes, shell execution, pairing, and interface opening; exact local allow rules can grant operations per transport, device, interface and operation.
- Extensible Python adapter interface, with optional transport dependencies loaded only when needed.

Broader non-advertising Wi-Fi/network scans, proprietary protocol inference, documentation search, and a graphical interface are extension points for later releases. ADB shell is limited by Android's own shell permissions. iOS does not expose a general-purpose shell; available services are those allowed by the device's iOS version, pairing/trust state and installed host support.

## Requirements

- Python 3.11 or newer.
- OS device permissions and transport drivers as applicable.
- Optional external tools/libraries for each transport (table below).

| Transport | Install | Host requirements |
| --- | --- | --- |
| USB | `pip install "universal-device-mcp[usb]"` | A libusb backend; some devices need a compatible driver. A kernel driver may own an interface. |
| USB HID | `pip install "universal-device-mcp[hid]"` | HIDAPI support from the OS; protected/system devices may deny access. |
| Serial/UART | `pip install "universal-device-mcp[serial]"` | Port permission on Linux/macOS; device driver on Windows. |
| Bluetooth LE | `pip install "universal-device-mcp[bluetooth]"` | Bluetooth adapter and OS permissions/services. |
| Local network | `pip install "universal-device-mcp[network]"` | Devices must advertise mDNS/DNS-SD TCP or UDP services; arbitrary IP ranges are not scanned. |
| Android | No Python extra | Android Platform Tools (`adb`) on `PATH`; USB debugging authorized on the phone. |
| iPhone/iPad | `pip install "universal-device-mcp[ios]"` | Uses `pymobiledevice3`. On Windows install the classic iTunes package for Apple Mobile Device Support; on Linux install and run `usbmuxd`; macOS uses the system usbmux service. Unlock the device and accept **Trust This Computer** for lockdown services. |

## Install

For copy-and-paste setup instructions for Claude Desktop, Claude Code, Codex, Cursor, VS Code, Cline, LM Studio, Ollama-backed models and Google Antigravity, see the [simple installation guide](docs/INSTALLATION.md).

### Quick setup for Claude Desktop, Cursor or VS Code

You do not need to clone the repository, create a Python environment, or know Python. Install `uv` once using its [official installer](https://docs.astral.sh/uv/getting-started/installation/). `uv` downloads the required Python version and the MCP dependencies when the server first starts.

In Claude Desktop, open **Settings → Developer → Edit Config**. In Cursor, open **Settings → MCP → Add Server**. Paste the `mcpServers` entry below into the configuration file (keep any other servers already there), save it, and restart the app:

```json
{
  "mcpServers": {
    "universal-device": {
      "command": "uvx",
      "args": [
        "--from",
        "universal-device-mcp[all] @ https://github.com/anonyme-afk/Universal-Device-MCP/archive/refs/heads/main.zip#subdirectory=Universal-Device-MCP-main",
        "universal-device-mcp"
      ]
    }
  }
}
```

The archive URL avoids requiring Git. The first start can take a few minutes while `uv` downloads and installs dependencies; later starts reuse them. For VS Code, use **MCP: Add Server** from the Command Palette and choose **stdio**, or save this in `.vscode/mcp.json`:

```json
{
  "servers": {
    "universal-device": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "universal-device-mcp[all] @ https://github.com/anonyme-afk/Universal-Device-MCP/archive/refs/heads/main.zip#subdirectory=Universal-Device-MCP-main",
        "universal-device-mcp"
      ]
    }
  }
}
```

See the official [VS Code MCP setup](https://code.visualstudio.com/docs/agents/reference/mcp-configuration), [Cursor MCP guide](https://docs.cursor.com/context/model-context-protocol), and [Claude Desktop local MCP guide](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop) for where each app stores its configuration.

To try the server without hardware, add `"env": { "UDMCP_ENABLE_SIMULATOR": "true" }` inside the server entry, restart the client, then ask the agent to discover the simulator. Remove that line when you are done; simulator entries are virtual devices.

### Run the published package

After a PyPI release, install and launch it with:

```bash
uvx --from "universal-device-mcp[all]" universal-device-mcp
```

Until a PyPI release is available, start directly from the GitHub source without installing Git:

```bash
uvx --from "universal-device-mcp[all] @ https://github.com/anonyme-afk/Universal-Device-MCP/archive/refs/heads/main.zip#subdirectory=Universal-Device-MCP-main" universal-device-mcp
```

For a developer checkout, use:

### Install from a checkout

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[all]"
```

The base install includes MCP SDK v2.3 or newer, which supports current MCP discovery and legacy clients. The `[all]` extra adds USB, HID, serial, BLE, network and iOS adapters. Install only the transports you need with `[usb]`, `[hid]`, `[serial]`, `[bluetooth]`, `[network]` or `[ios]`. For Android-only use, install the base package and Android Platform Tools separately.

Start the server directly:

```bash
universal-device-mcp
# or
python -m universal_device_mcp.server
```

The process uses MCP stdio; do not type into its terminal while it is running. MCP protocol messages use stdout, so diagnostics should go to stderr.

### MCP client configuration

Example for a client that accepts a local stdio server configuration (replace paths for your machine):

```json
{
  "mcpServers": {
    "universal-device": {
      "command": "uvx",
      "args": [
        "--from",
        "universal-device-mcp[all] @ https://github.com/anonyme-afk/Universal-Device-MCP/archive/refs/heads/main.zip#subdirectory=Universal-Device-MCP-main",
        "universal-device-mcp"
      ],
      "env": {
        "UDMCP_DATABASE": "C:/Users/you/AppData/Local/UniversalDeviceMCP/devices.sqlite3",
        "UDMCP_POLICY": "C:/Users/you/.config/udmcp/policy.json"
      }
    }
  }
}
```

The same `uvx` configuration works on macOS and Linux when `uv` is on `PATH`. For a local checkout, set `command` to the virtual environment's Python and `args` to `["-m", "universal_device_mcp.server"]`. Use absolute paths. Restart the MCP client after changing configuration.

## MCP tools

| Tool | Purpose |
| --- | --- |
| `get_runtime_status()` | Check installed transports and host prerequisites without starting a hardware scan. |
| `discover_devices(transports?)` | Scan selected or all installed transports; each adapter reports its own errors. |
| `discover_wireless_devices()` | Scan BLE, local mDNS TCP/UDP services, wireless ADB services and paired iOS Bonjour services. |
| `pair_android_over_wifi(endpoint, pairing_code)` / `connect_android_over_wifi(endpoint)` | Pair and connect only to endpoints currently advertised by ADB mDNS. |
| `list_known_devices()` | List locally remembered profiles. |
| `start_device_monitor(interval_seconds?)` / `stop_device_monitor()` | Start or stop background monitoring. It is off by default. |
| `get_device_events(after_id?, limit?)` | Read persistent connect/disconnect events after a cursor. |
| `inspect_device(device_id)` | Return stored identity/interfaces and query transport-specific details. |
| `open_interface(device_id, interface_id, options?)` / `close_interface(session_id)` | Open or release a persistent USB, HID, serial, TCP or UDP interface session. |
| `communicate(device_id, interface_id, operation, data_hex?, session_id?, options?)` | Generic low-level transport I/O; iOS commands use an argv array and are pinned to the selected UDID. Bytes use hexadecimal strings; an open session can be reused where supported. |
| `communicate_many(targets, operation="read")` | Concurrent read/receive on up to 32 exact device/interface pairs (bounded to 16 active reads); results and failures stay separate per target. |
| `create_device_group(name, selector)` / `list_device_groups()` / `inspect_device_group(group_id)` / `delete_device_group(group_id)` | Save and inspect selector-based groups while preserving each device's own identity. |
| `read_device_group(group_id, interface_id, operation="read", options?)` | Read/receive from connected and remembered group members concurrently; disconnected and failed targets get individual results. |
| `prepare_group_write(...)` / `execute_approved_group_write(approval_id)` | Freeze an exact group target set (maximum 32 devices and 4 KiB payload), validate each target against local policy, then request client-side MCP elicitation before one-time execution. Requires elicitation support; partial completion is possible. |
| `explain_device_interface(device_id, interface_id)` / `get_device_capabilities(device_id)` / `run_device_diagnostics(device_id)` / `get_supported_protocols()` / `generate_device_report(device_id?)` | Explain observed interfaces, summarize known information and produce diagnostics/reports without claiming unknown protocols are understood. |
| `analyze_payload(data_hex, baseline_hex?)` | Decode common byte views and compare samples; outputs are hypotheses, not protocol identification. |
| `remember_discovery(device_id, category, content, confidence?, source?)` | Append an explicit hypothesis or confirmed finding. |
| `update_device_profile(device_id, updates)` | Edit saved name and metadata; the physical fingerprint and transport stay fixed. |
| `get_device_knowledge(device_id)` | Return profile, discoveries and recent experiment history. |
| `export_device_profile(device_id)` | Export one complete profile as JSON text. |
| `forget_device(device_id)` | Delete one profile, discoveries and experiments. |
| `get_access_policy()` | Show the local access mode (`safe`, `trusted`, or `full`) and active per-device policy. |
| `discover_cameras(max_index?)` / `capture_camera_image(camera_index?)` | Explicitly probe cameras or capture one bounded JPEG in memory; camera access is disabled unless the owner sets `UDMCP_MEDIA_CAPTURE=true`. |
| `discover_microphones()` / `record_audio_sample(duration_seconds?, device_index?)` | List audio inputs or explicitly capture at most 10 seconds of WAV in memory; capture is owner-enabled and never saved. |

With the official MCP SDK, tools that return objects provide structured MCP output as well as readable text for clients that only consume text. Read-only resources are available at `udmcp://devices` and `udmcp://devices/{device_id}/profile`; the latter contains that device's saved profile, discoveries and retained experiment metadata. The repository includes [the V1 acceptance specification](docs/PRODUCT_V1.md) and [the V2 distributed-platform specification](docs/PRODUCT_V2.md). V2 includes the V1 product as its local node; neither specification is a claim that every release gate is already complete.

### Generic communication examples

First call `discover_devices`, then use the returned `device_id` and `interface_id` values. Inspect interfaces before communicating; do not guess endpoint addresses or protocol commands.

For cable-free Android access, enable **Developer options → Wireless debugging** on the phone and put it on the same Wi-Fi network as the computer. Call `discover_wireless_devices`; when the phone shows a pairing service, pass its exact endpoint and the six-digit code shown on the phone to `pair_android_over_wifi`. Then discover again and call `connect_android_over_wifi` with the advertised TLS connect endpoint. The device must authorize the workstation; afterward it appears in ordinary ADB discovery and supports the same inspection and shell tools as a USB-connected phone. The server does not scan arbitrary IP addresses. Android's official ADB guidance requires pairing and mDNS discovery on the same network: [Wireless debugging requirements](https://developer.android.com/tools/adb).

BLE devices can also be discovered with `discover_wireless_devices` or `discover_devices(transports=["bluetooth"])`. Use `inspect_device` to enumerate GATT services and characteristics, then `communicate` with the characteristic UUID as the interface. This supports BLE GATT; Bluetooth Classic profiles require a separate adapter.

### iPhone and iPad

Install the `[ios]` extra and the host components listed above, then connect the device by USB. `discover_devices(transports=["ios"])` uses `pymobiledevice3 usbmux list` to find iOS devices. If usbmux cannot provide lockdown access, the adapter also attempts a read-only Apple USB descriptor scan through PyUSB; this can identify an attached Apple device while locked, but only basic descriptors are available and USB Restricted Mode, the host driver, or the OS may prevent even that. It never bypasses the device passcode or trust prompt.

After unlocking the device and approving **Trust This Computer**, call `inspect_device` for lockdown information. `discover_wireless_devices` also lists Apple mobdev2 Bonjour advertisements when this computer already has the required pairing record. To use another documented `pymobiledevice3` operation, call `communicate` with `interface_id="ios-cli"`, `operation="execute"`, and `options={"argv": ["apps", "list"]}`. The server launches the installed CLI without a shell and fixes the target UDID. These commands can modify device state; use the specific operation the owner requested. iOS does not provide an Android-style arbitrary shell, and some developer services on iOS 17+ require a developer tunnel and Developer Mode.

Serial write: `operation="write"`, `data_hex="48454c500a"`, options such as `{"baudrate": 115200}`. Serial read: `operation="read"`, options `{"baudrate": 115200, "length": 128}`. Serial sessions also accept `bytesize`, `parity`, `stopbits`, `xonxoff`, `rtscts`, and `dsrdtr` where the OS driver supports them.

USB endpoint read: `operation="read"`, options `{"endpoint": "0x81", "length": 64}`. USB write uses the device-reported OUT endpoint and a deliberate hex payload. Control transfers use `control_read` or `control_write`, with `bmRequestType`, `bRequest`, and optional `wValue`/`wIndex`; a control write also needs `data_hex`. If an interface is in a non-active USB configuration, open it with `set_configuration=true` to explicitly switch configurations before claiming it; one-shot transfers do not switch configurations.

For serial, USB, HID, TCP and UDP transports that support persistent handles, call `open_interface` once and pass the returned `session_id` to each `communicate` call. Call `close_interface` when finished. Sessions are closed automatically on device removal or server shutdown.

BLE read/write: use the characteristic UUID as `interface_id` or set `options.characteristic_uuid`. ADB execution: `interface_id="shell"`, `operation="execute"`, options `{"argv": ["getprop", "ro.product.model"]}`. ADB accepts an argument array rather than a shell command string.

HID report I/O uses `interface_id="hid-report"`; select `read`/`receive` or `write`/`send` and provide the report bytes in hex. Report IDs and report layouts are device-specific and must be learned from documentation or careful inspection.

For a discovered mDNS service, use `interface_id="tcp"` or `"udp"` according to its advertised protocol, with `operation="read"`, `"write"`, or `"communicate"` and a deliberate hex payload. Network discovery only lists services advertised on the local network; it does not probe arbitrary hosts or ports. Generic network communication can still change a service's state, so inspect the service and follow the owner's instructions.

## Local memory

The default database lives in the operating system's per-user application data directory under `UniversalDeviceMCP/devices.sqlite3`. Override it using `UDMCP_DATABASE`. The database uses SQLite foreign keys and write-ahead logging. Device identity is matched by transport fingerprint; each profile also reports `identity.fingerprint_basis` so an agent can tell whether identification used a hardware serial, physical port topology, or a less stable host address. Discovery compares stable identity, hardware and interface data while ignoring volatile USB addresses, BLE RSSI and advertisement payloads. Discoveries are append-only and explicitly tagged `hypothesis` or `confirmed`; communication attempts are recorded as experiments. Back up the database file while the server is stopped for a consistent portable copy.

Each changed hardware/interface configuration is preserved as a snapshot. Connect/disconnect events are stored locally and can be fetched incrementally with `get_device_events` by passing the last returned event id as `after_id`. By default, raw request and response payloads are replaced with their length and SHA-256 hash; set `UDMCP_STORE_PAYLOADS=true` only if raw payload retention is necessary. Experiments, events and snapshots older than 30 days are purged when the server starts; change this with `UDMCP_RETENTION_DAYS`, or set it to `0` to clear history on startup. Device profiles and validated discoveries remain until removed. `forget_device` deletes one profile and its associated records. Protect the database as you would other device metadata.

No cloud service is required. Local network discovery uses mDNS/DNS-SD multicast. The network adapter sends only the payload explicitly supplied by the agent to a previously discovered service. BLE scanning uses the host Bluetooth stack; ADB and hardware drivers perform their normal host communication.

## Safety and permissions

Low-level writes and ADB shell execution can change device state. Client annotations are descriptive, not an authorization mechanism; the server enforces its local policy. Names, service advertisements, descriptors and payloads supplied by devices are untrusted data, never instructions. The OS and installed drivers remain the actual permission boundary. A device must appear in a current discovery result before opening an interface or communicating. Raw payloads are capped at 1 MiB, with tighter read caps for HID. USB kernel-driver detachment is off by default and requires the explicit `detach_kernel_driver=true` option. Never send undocumented writes to safety-critical, medical, industrial, or firmware interfaces. Disconnecting or timing out a transport operation may not undo an action already received by a device.

Writes and interface opening are denied unless `UDMCP_POLICY` points to a local JSON allowlist. Reads and inspection remain available. Each allow rule must name the exact transport, device ID (or fingerprint), interface ID, and operation; rules do not inherit wildcards. Explicit denies take precedence. Example:

```json
{
  "allowed_operations": [
    {"transport": "serial", "device_id": "serial:USB-SERIAL-123", "interface_id": "COM4", "operation": "write"}
  ],
  "max_write_bytes": 4096
}
```

`max_write_bytes` defaults to 4096. An explicit write authorization does not mean an interactive confirmation was collected from the current MCP client; configure the local allowlist only for operations you intend to permit. Policy changes take effect on the next call. Monitoring is disabled by default; `UDMCP_AUTO_MONITOR=true` opts into automatic scans. BLE and mDNS discovery remain on demand.

### Local access modes

The computer owner may set `UDMCP_ACCESS_MODE` in the MCP server's local environment. The default is `safe`, which keeps exact per-device policy rules for mutations. `trusted` also permits the standard read/open/write operations for devices whose exact ID or fingerprint is listed in the local `UDMCP_POLICY` JSON `trusted_devices` array. `full` permits supported non-critical adapter operations without per-operation allow rules. Explicit deny rules, OS permissions, adapter limits, payload caps and audit history still apply in every mode. Firmware flashing, erase/wipe/format, delete/remove, arbitrary execute, factory reset and bootloader unlock operations are blocked in all three modes. The agent cannot change the process environment or select a mode through an MCP tool.

### Camera and microphone capture

Install media support with `pip install "universal-device-mcp[media]"` (or add `[media]` to the package extras used by your client). The computer owner must additionally set `UDMCP_MEDIA_CAPTURE=true`; otherwise capture tools fail closed. `discover_cameras` probes indexes only when explicitly called and may briefly turn cameras on. `capture_camera_image` returns one JPEG (up to 900 KB) in memory. `discover_microphones` lists input devices without opening them; `record_audio_sample` captures up to 10 seconds of mono 16 kHz WAV in memory. Captures are never written to disk or retained in device history. Windows/macOS privacy settings, Linux camera/audio services and drivers remain authoritative. Continuous video/audio streams, adjustable camera controls, image analysis, and transcription are not implemented in this initial capture release.

### Try without hardware

Set `UDMCP_ENABLE_SIMULATOR=true` in the MCP client's environment, then call `discover_devices` with `transports=["simulator"]` and `communicate_many` with the two returned IDs and `interface_id="telemetry"`. The simulator returns clearly marked sample data and does not touch physical hardware.

## Multi-computer hub (V2 foundation)

The local MCP can also act as an authenticated remote node. A hub aggregates inventory from a fixed list of nodes and can issue bounded parallel **reads only**. Remote write tools are intentionally not exposed; each node's local policy remains authoritative. This initial hub mode is single-tenant and uses a shared bearer token per node, not OIDC, mTLS, enrollment, or a distributed job queue. Put the node behind HTTPS before connecting over a network.

On each node, set a random secret of at least 32 characters and start the server with `UDMCP_ROLE=node`, `UDMCP_TRANSPORT=streamable-http`, `UDMCP_NODE_TOKEN`, and `UDMCP_RESOURCE_URL` set to that node's HTTPS MCP URL. For a local smoke setup only, bind to `127.0.0.1` and use an `http://localhost:8000/mcp` resource URL is not accepted; node resources must be HTTPS. On a real host, terminate TLS at a trusted reverse proxy and set `UDMCP_HTTP_HOST=127.0.0.1` behind it. Node HTTP defaults to loopback and port 8000.

On the hub, configure `UDMCP_REMOTE_NODES` as a JSON array and provide each token through the named environment variable (never put the secret in the JSON):

```json
[{"node_id":"workshop","organization_id":"default","site":"home","url":"https://device-host.example/mcp","token_env":"UDMCP_WORKSHOP_TOKEN"}]
```

The hub's MCP client can then call `list_remote_nodes`, `discover_remote_devices`, and `read_remote_devices`. The last tool requires exact `node_id`, `device_id`, and `interface_id` values from discovery; it accepts at most 32 unique targets and preserves per-device errors. Details and remaining V2 release requirements are tracked in [the V2 specification](docs/PRODUCT_V2.md).

## Development

```bash
python -m pip install -e ".[all,dev]"
python -m pytest -q
python -m ruff check src tests
python -m universal_device_mcp.server
```

GitHub Actions runs tests and lint across Windows, Linux, macOS and Python 3.11–3.13. It also starts the server through the official MCP Inspector CLI and checks tool discovery.

Adapters implement `Adapter` in `src/universal_device_mcp/adapters/base.py`. Implement `discover()` and `communicate()`, and optionally `inspect()`. Third-party Python packages can register an adapter factory through the `universal_device_mcp.adapters` entry-point group; the server loads these plugins automatically and reports load failures as discovery errors. Optional dependencies should be imported inside adapter methods so one missing library does not prevent other transports from starting.

For a Python package using setuptools, register the factory in its `pyproject.toml`:

```toml
[project.entry-points."universal_device_mcp.adapters"]
my_transport = "my_package.adapter:MyAdapter"
```

`MyAdapter` can be an `Adapter` subclass or a compatible object that exposes `transport`, `discover()` and `communicate()`. Its factory is called with no arguments.

## Troubleshooting

- **No USB devices:** install the optional extra and a supported libusb backend; check driver ownership and OS permissions. Some keyboards, storage devices and system devices should not be claimed through libusb.
- **No serial ports:** install a device driver, check the selected port and OS group/permission, and close other applications using the port.
- **HID errors:** install the `hid` extra and check that the OS permits access to the selected report interface.
- **BLE errors:** ensure Bluetooth is enabled and grant application permission in the OS. BLE availability differs by OS and adapter.
- **No local network services:** install the `network` extra; only mDNS/DNS-SD-advertised TCP/UDP services are found.
- **iPhone/iPad is missing:** install the `[ios]` extra. Windows requires Apple's Mobile Device Support (provided by the classic iTunes installer); Linux requires a running `usbmuxd`; macOS uses its system service. Unlock the device and accept **Trust This Computer** for detailed lockdown access. Before that, only usbmux discovery or best-effort USB descriptors may be available, subject to the OS, cable, USB permissions and backend.
- **ADB shows unauthorized/offline:** the device remains visible in discovery with its state, but no shell interface is exposed until it reaches the authorized `device` state. Unlock the phone and accept its USB debugging prompt.
- **MCP server will not start:** verify the client launches the same Python environment where the `mcp` package is installed; inspect the MCP client's stderr/logs.
- **Profile database location:** set `UDMCP_DATABASE` to an absolute writable file path.

## Roadmap

Structured USB HID report-descriptor parsing, discovery of non-advertising network devices, Bluetooth Classic, camera/microphone OS APIs, broader protocol/documentation knowledge sources, GUI, and richer import workflows remain planned. Automatic proprietary protocol discovery is inherently uncertain and is not claimed as a completed feature.

## License

MIT. See [LICENSE](LICENSE).

