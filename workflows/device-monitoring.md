# Workflow: Device Connection Monitoring

## Objective

Start background monitoring of hardware connections and disconnections, reacting to state changes in real time.

## Preconditions

- Universal Device MCP server is running.
- `UDMCP_AUTO_MONITOR` can remain at default (`false`: explicit start required).

## Recommended Sequence

1. **Start the monitor**: `start_device_monitor(interval_seconds=5.0)`
   - The background monitor periodically scans for connected and disconnected devices.
2. **Read events**: `get_device_events(after_id=0, limit=100)`
   - Fetch connection and disconnection events since the last known event ID.
3. **Handle events**:
   - `connected`: Inspect the new device (`inspect_device`).
   - `disconnected`: Mark the device as unavailable, avoid sending further operations to its `device_id`.
4. **Stop the monitor**: `stop_device_monitor()` when active monitoring is no longer needed.

## MCP Tools Used

- `start_device_monitor`
- `stop_device_monitor`
- `get_device_events`
- `inspect_device`

## Expected Output

- Event entries with `type` (`connected` or `disconnected`), `device_id`, `details`, and `created_at`.
- Up-to-date connection status for all known devices.

## Error Handling

| Situation | Action |
|-----------|--------|
| Event references unknown device | Run `discover_devices` to refresh the local inventory. |
| Device disconnects during an operation | Operation fails with `RuntimeError` or `TimeoutError`. Re-run `inspect_device` to confirm current state. |

## Security Considerations

- The monitor operates in read-only mode regarding device state; it never alters hardware configurations.
- The background monitor is stopped by default and requires explicit activation.
