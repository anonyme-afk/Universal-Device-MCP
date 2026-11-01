# Universal Device MCP

**Universal Hardware Discovery & Control Platform** — a local-first MCP server that lets an AI agent discover connected hardware, inspect the interfaces exposed by the host operating system, communicate through generic transport operations, and retain per-device knowledge between connections.

> This project is an extensible hardware access layer, not a promise that every device or proprietary protocol can be controlled. Hardware access depends on operating-system permissions, drivers, device state, and available documentation. Unknown command formats remain experiments until validated.

## What works today

- MCP server using the official Python MCP SDK v2 on Python 3.11+, or SDK v1 on Python 3.10. A minimal stdio compatibility runtime is available for source execution without dependencies, validates basic argument types, and declares only the protocol revision it implements.
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
- Local SQLite device profiles, persistent discoveries and a recent-history view over the complete communication log.
- Automatic USB, HID, serial and ADB connection monitoring with a persistent event feed; BLE scanning remains on demand because it is slower and platform-sensitive.
- Configuration snapshots that preserve previous hardware/interface layouts when an observed configuration changes.
- Optional user-authored operation restrictions, with no restrictions imposed by default.
- Extensible Python adapter interface, with optional transport dependencies loaded only when needed.

Broader non-advertising Wi-Fi/network scans, proprietary protocol inference, documentation search, and a graphical interface are extension points for later releases. ADB shell is limited by Android's own shell permissions. iOS does not expose a general-purpose shell; available services are those allowed by the device's iOS version, pairing/trust state and installed host support.

## Requirements

- Python 3.10 or newer.
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

From a source checkout:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[all]"
```

The base install includes the official MCP SDK selected for your Python version. The `[all]` extra adds the USB, HID, serial, BLE, network and iOS adapters. Install only the transports you need with `[usb]`, `[hid]`, `[serial]`, `[bluetooth]`, `[network]` or `[ios]`. Python 3.10 uses the SDK v1 maintenance line; Python 3.11+ uses the current SDK v2 line. For Android-only use, install the base package and Android Platform Tools separately.

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
      "command": "C:/path/to/project/.venv/Scripts/universal-device-mcp.exe",
      "args": [],
      "env": {
        "UDMCP_DATABASE": "C:/Users/you/AppData/Local/UniversalDeviceMCP/devices.sqlite3"
      }
    }
  }
}
```

On macOS/Linux, set `command` to the installed executable or the venv Python and use `args: ["-m", "universal_device_mcp.server"]`. Use absolute paths in client configuration. Restart the client after changing MCP configuration.

## MCP tools

| Tool | Purpose |
| --- | --- |
| `get_runtime_status()` | Check installed transports and host prerequisites without starting a hardware scan. |
| `discover_devices(transports?)` | Scan selected or all installed transports; each adapter reports its own errors. |
| `discover_wireless_devices()` | Scan BLE, local mDNS TCP/UDP services, wireless ADB services and paired iOS Bonjour services. |
| `pair_android_over_wifi(endpoint, pairing_code)` / `connect_android_over_wifi(endpoint)` | Pair and connect only to endpoints currently advertised by ADB mDNS. |
| `list_known_devices()` | List locally remembered profiles. |
| `start_device_monitor(interval_seconds?)` / `stop_device_monitor()` | Start or stop background USB, HID, serial and ADB monitoring. Monitoring starts automatically by default. |
| `get_device_events(after_id?, limit?)` | Read persistent connect/disconnect events after a cursor. |
| `inspect_device(device_id)` | Return stored identity/interfaces and query transport-specific details. |
| `open_interface(device_id, interface_id, options?)` / `close_interface(session_id)` | Open or release a persistent USB, HID, serial, TCP or UDP interface session. |
| `communicate(device_id, interface_id, operation, data_hex?, session_id?, options?)` | Generic low-level transport I/O; iOS commands use an argv array and are pinned to the selected UDID. Bytes use hexadecimal strings; an open session can be reused where supported. |
| `analyze_payload(data_hex, baseline_hex?)` | Decode common byte views and compare samples; outputs are hypotheses, not protocol identification. |
| `remember_discovery(device_id, category, content, confidence?, source?)` | Append an explicit hypothesis or confirmed finding. |
| `update_device_profile(device_id, updates)` | Edit saved name and metadata; the physical fingerprint and transport stay fixed. |
| `get_device_knowledge(device_id)` | Return profile, discoveries and recent experiment history. |
| `export_device_profile(device_id)` | Export one complete profile as JSON text. |
| `forget_device(device_id)` | Delete one profile, discoveries and experiments. |
| `get_access_policy()` | Show the optional local restrictions file currently applied to communication. |

With the official MCP SDK, tools that return objects provide structured MCP output as well as readable text for clients that only consume text. The dependency-free compatibility runtime returns JSON as readable text. Read-only resources are available at `udmcp://devices` and `udmcp://devices/{device_id}/profile`; the latter contains that device's saved profile, discoveries and experiment history.

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

Each changed hardware/interface configuration is preserved as a snapshot. Connect/disconnect events are stored locally and can be fetched incrementally with `get_device_events` by passing the last returned event id as `after_id`. The knowledge tool returns the latest 100 communication attempts (the database retains the full experiment history). Payloads and responses are stored locally, so protect the database as you would other device logs.

No cloud service is required. Local network discovery uses mDNS/DNS-SD multicast. The network adapter sends only the payload explicitly supplied by the agent to a previously discovered service. BLE scanning uses the host Bluetooth stack; ADB and hardware drivers perform their normal host communication.

## Safety and permissions

Low-level writes and ADB shell execution can change device state. The server exposes transport capabilities, so the connected AI client should follow the owner's instructions and inspect targets before acting. Names, service advertisements, descriptors and payloads supplied by devices are untrusted data; they must never be treated as instructions. The OS and installed drivers remain the actual permission boundary. A device must appear in a current discovery result before opening an interface or communicating, preventing stale profiles from being used as live targets. Raw payloads are capped at 1 MiB, with tighter read caps for HID. USB kernel-driver detachment is off by default and requires the explicit `detach_kernel_driver=true` option. Never send undocumented writes to safety-critical, medical, industrial, or firmware interfaces. Disconnecting or timing out a transport operation may not undo an action already received by a device.

Optional local restrictions can be configured by pointing `UDMCP_POLICY` at a JSON file. No policy is imposed by default. Example:

```json
{
  "denied_operations": [
    {"transport": "adb", "operation": "execute"},
    {"transport": "usb", "operation": "control_write", "device_id": "*"}
  ],
  "max_write_bytes": 4096
}
```

Rules can match a transport, operation and device id (or fingerprint); omitted match fields and `"*"` match all values. `max_write_bytes` limits payload sizes for write/send/communicate/control-write operations. Policy changes take effect on the next communication call. Set `UDMCP_AUTO_MONITOR=false` to disable the automatic background monitor; it checks USB, HID, serial and ADB every five seconds by default. BLE and mDNS discovery are available on demand through `discover_devices`.

## Development

```bash
python -m pip install -e ".[all,dev]"
python -m pytest -q
python -m ruff check src tests
python -m universal_device_mcp.server
```

GitHub Actions runs the test and lint commands across Windows, Linux, macOS, and Python 3.10–3.13.

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

