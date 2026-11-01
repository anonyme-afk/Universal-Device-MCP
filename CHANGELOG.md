# Changelog

## Unreleased

- Add persisted selector-based multi-device groups, concurrent per-device reads, and one-time group-write approval through MCP elicitation.
- Bound group writes to 32 devices and 4 KiB, show the complete request details during client approval, and preserve per-target partial results.
- Add capability summaries, interface explanations, diagnostics and device reports.
- Replace loopback-dependent network adapter tests with deterministic socket fakes to avoid OS-specific CI failures.
- Update V2 specification so it includes V1 as its node runtime and make current incomplete release gates explicit.

## 0.2.0

- Require Python 3.11+ and the official MCP Python SDK v2; remove the handwritten MCP protocol fallback.
- Deny writes, command execution, pairing, connection setup, and interface opening by default; allow exact local policy rules.
- Stop retaining raw communication payloads by default and purge old history according to configurable retention.
- Disable automatic monitoring by default.
- Discover adapters concurrently and add bounded per-target concurrent read operations.
- Add a deterministic two-device simulator and automated MCP Inspector CLI smoke check.
- Add copyable uv installation/client configuration, security guidance, and contribution documentation.
