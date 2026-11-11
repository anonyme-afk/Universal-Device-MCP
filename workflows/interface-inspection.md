# Workflow: Device Interface Inspection

## Objective

Inspect and understand which interfaces a target device exposes and what operations can be safely performed on them.

## Preconditions

- A known `device_id` (obtained via `discover_devices` or `list_known_devices`).

## Recommended Sequence

1. **Inspect the device**: `inspect_device(device_id)`
   - Verify that the device is connected (`connected: true`).
   - Check the list of `interfaces` (each interface has an `id` and a `kind`).
2. **Explain a specific interface**: `explain_device_interface(device_id, interface_id)`
   - Retrieve a human-readable explanation of what the interface represents and its supported operations.
3. **Inspect device capabilities**: `get_device_capabilities(device_id)`
   - Quick overview of observed interfaces and validated protocols.

## MCP Tools Used

- `inspect_device`
- `explain_device_interface`
- `get_device_capabilities`

## Expected Output

For each interface:
- `id`: Interface identifier (used in `communicate_device`, `open_interface`, etc.).
- `kind`: Interface type (e.g. `adb-shell`, `usb-bulk`, `gatt-characteristic`, `serial-port`).
- Clear, readable descriptions of available operations for the AI agent.

## Error Handling

| Situation | Action |
|-----------|--------|
| `KeyError: Unknown device` | `device_id` does not exist. Re-run `discover_devices` to obtain a fresh, valid ID. |
| Device disconnected | Call `connect_device(device_id)` then re-inspect. |
| No interfaces returned | The device exposes no usable interfaces in its current state. |

## Security Considerations

- Inspection is strictly read-only. It never modifies any hardware state.
- Never assume an interface supports an operation without first checking `explain_device_interface`.
