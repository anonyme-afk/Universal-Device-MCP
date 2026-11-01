# Changelog

## 0.2.0

- Require Python 3.11+ and the official MCP Python SDK v2; remove the handwritten MCP protocol fallback.
- Deny writes, command execution, pairing, connection setup, and interface opening by default; allow exact local policy rules.
- Stop retaining raw communication payloads by default and purge old history according to configurable retention.
- Disable automatic monitoring by default.
- Discover adapters concurrently and add bounded per-target concurrent read operations.
- Add a deterministic two-device simulator and automated MCP Inspector CLI smoke check.
- Add copyable uv installation/client configuration, security guidance, and contribution documentation.
