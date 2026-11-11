# Workflow: Connected Hardware Discovery

## Objective

List all hardware devices accessible through local adapters (USB, serial, Bluetooth, mDNS network, Android ADB, iOS) and build a structured inventory.

## Preconditions

- Universal Device MCP server is running.
- The agent has access to `discover_devices`, `discover_wireless_devices`, `list_known_devices`, and `get_runtime_status`.

## Recommended Sequence

1. **Check server status**: `get_runtime_status`
   - Confirm that desired adapters are available without missing dependency errors.
2. **Discover local devices**: `discover_devices`
   - Optional: filter by transport if looking for a specific type (`transports=["usb"]`, `transports=["serial"]`, etc.).
3. **Discover wireless & network devices**: `discover_wireless_devices`
   - Probes BLE peripherals, mDNS services, local Android ADB daemons, and iOS devices.
4. **List previously remembered devices**: `list_known_devices`
   - Inspect already recorded device profiles in the local SQLite database.

## MCP Tools Used

- `get_runtime_status`
- `discover_devices`
- `discover_wireless_devices`
- `list_known_devices`

## Expected Output

A list of detected devices, each containing:
- `device_id`: Stable identifier to use for subsequent inspection and operations.
- `transport`: Connection type (usb, serial, bluetooth, network, adb, ios, simulator).
- `name`: Human-readable device name.
- `fingerprint`: Stable hardware fingerprint.
- `interfaces`: List of exposed interfaces (`id`, `kind`, etc.).

## Error Handling

| Situation | Action |
|-----------|--------|
| No devices found | Verify hardware is physically plugged in and adapter drivers/extras are installed. Re-run `discover_devices`. |
| Missing dependency (`ImportError`) | Check `get_runtime_status` to see which adapter failed. Install the corresponding Python package extra. |
| OS permission error | Operating system access restricted. Check privacy permissions (Camera, Microphone, Bluetooth, USB). |

## Security Considerations

- Hardware discovery is strictly read-only. It never modifies any hardware state.
- No physical device is energized or activated beyond bus enumeration.
- Discovery results are persisted into the local SQLite database only when `remember_discovery` is explicitly invoked.
