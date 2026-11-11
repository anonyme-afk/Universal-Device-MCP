# Workflow: Audio Recording with a Microphone

## Objective

Detect available microphones and capture an in-memory WAV audio sample.

## Preconditions

- `UDMCP_MEDIA_CAPTURE=true` must be set in the server environment (owner opt-in).
- The `[media]` package extra must be installed (`opencv-python-headless`, `sounddevice`, `numpy`).

## Recommended Sequence

1. **Verify media permissions**: Check that `UDMCP_MEDIA_CAPTURE=true` or query `get_access_policy`.
2. **Discover microphones**: `discover_microphones()`
   - Lists audio input devices without opening an active recording stream.
3. **Record a sample**: `record_audio_sample(duration_seconds=3.0, device_index=None)`
   - Duration between 0.25 and 10 seconds.
   - Returns in-memory, base64-encoded mono 16 kHz WAV audio.
   - Audio is never written to disk and is not stored in history.

## MCP Tools Used

- `discover_microphones`
- `record_audio_sample`

## Expected Output

- List of microphones with `device_id`, `index`, `name`, `max_input_channels`, `default_samplerate`.
- Captured audio: `mime_type: audio/wav`, `audio_base64`, `sample_rate_hz: 16000`, `channels: 1`, `duration_seconds`, `persisted: false`.

## Error Handling

| Situation | Action |
|-----------|--------|
| `PermissionError` | `UDMCP_MEDIA_CAPTURE` is not set. Ask the computer owner to enable it locally. |
| `ImportError` | The `[media]` extra is not installed. Run `pip install "universal-device-mcp[media]"`. |
| `ValueError` | `duration_seconds` must be between 0.25 and 10. Correct the parameter. |
| No microphone found | No audio input device detected. Verify physical connection and OS microphone privacy permissions. |

## Security Considerations

- No microphone is recorded in the background by default. `record_audio_sample` requires an explicit tool call.
- Audio is held strictly in memory and is never written to disk.
- Respect host OS privacy settings (Windows, macOS, Linux).
