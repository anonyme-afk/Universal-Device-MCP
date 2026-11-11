# Workflow: Device Interaction

## Objective

Send a generic operation to a device interface and verify the operation's outcome.

## Preconditions

- A known `device_id` and `interface_id` (obtained via `discover_devices` and `inspect_device`).
- The local access policy authorizes the operation (`get_access_policy` checked).
- The device is connected (`connect_device` called if needed).

## Recommended Sequence

1. **Check access policy**: `get_access_policy`
   - Confirm current access mode (`safe`, `trusted`, `full`, `unrestricted`) and verify the operation is not blocked.
2. **Verify connection**: `inspect_device(device_id)`
   - If `connected: false`, call `connect_device(device_id)`.
3. **Execute operation**: `communicate_device(device_id, interface_id, operation, data_hex?, session_id?, options?)`
   - `operation`: name of the operation (e.g. `read`, `write`, `send`, `communicate`).
   - `data_hex`: hexadecimal payload data when applicable.
   - `session_id`: reuse an open session if supported by the interface.
4. **Verify result**: verify absence of error and validate data integrity.

## MCP Tools Used

- `get_access_policy`
- `inspect_device`
- `connect_device` (if necessary)
- `communicate_device`
- `open_interface` / `close_interface` (if persistent session is required)

## Expected Output

- Returned payload data from the hardware (for read operations).
- Send acknowledgment (for write operations).
- No error field in response payload.

## Error Handling

| Situation | Action |
|-----------|--------|
| `PermissionError` | Local policy blocks the operation. Ask the user/owner to configure an exact local rule in `UDMCP_POLICY`. |
| `RuntimeError: not currently connected` | Call `connect_device(device_id)` then retry. |
| `TimeoutError` | Device is not responding. Check physical cable/connection and re-run `inspect_device`. |
| `ValueError` | Invalid parameter (e.g. malformed `data_hex`). Correct input parameters. |

## Security Considerations

- Never execute destructive operations (`flash`, `wipe`, `format`, `delete`, `remove`, `factory_reset`, `bootloader_unlock`, `execute`) without explicit authorization. They are blocked in all safe/trusted/full modes, and require explicit one-time confirmation in `unrestricted` mode.
