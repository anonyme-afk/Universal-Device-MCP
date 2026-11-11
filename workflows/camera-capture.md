# Workflow: Image Capture with a Camera

## Objective

Detect available cameras and capture an in-memory JPEG frame.

## Preconditions

- `UDMCP_MEDIA_CAPTURE=true` must be set in the server environment (owner opt-in).
- The `[media]` package extra must be installed (`opencv-python-headless`, `sounddevice`, `numpy`).

## Recommended Sequence

1. **Verify media permissions**: `get_access_policy` or check `UDMCP_MEDIA_CAPTURE=true`.
2. **Discover cameras**: `discover_cameras(max_index=8)`
   - Each probe may briefly activate the camera hardware. Do not call automatically without explicit user intent.
3. **Capture a frame**: `capture_camera_image(camera_index=0)`
   - Returns an in-memory, base64-encoded JPEG image (≤ 900 KB).
   - The image is never written to disk and is not stored in history.

## MCP Tools Used

- `discover_cameras`
- `capture_camera_image`

## Expected Output

- List of detected cameras with `device_id` and `index`.
- Captured frame: `mime_type: image/jpeg`, `image_base64`, size in bytes, `persisted: false`.

## Error Handling

| Situation | Action |
|-----------|--------|
| `PermissionError` | `UDMCP_MEDIA_CAPTURE` is not set. Ask the computer owner to enable it locally. |
| `ImportError` | The `[media]` extra is not installed. Run `pip install "universal-device-mcp[media]"`. |
| No camera found | No camera accessible at probed indices. Verify physical connection and ensure no other application is locking the camera. |

## Security Considerations

- No camera is activated automatically. `discover_cameras` and `capture_camera_image` require explicit tool calls.
- Image frames are kept strictly in memory and are never persisted to disk.
- Respect host OS privacy and device permission settings (Windows, macOS, Linux).
