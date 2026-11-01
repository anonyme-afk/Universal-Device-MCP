# Security Policy

## Supported versions

Security fixes are prepared for the latest release on the `main` branch.

## Reporting a vulnerability

Please do not disclose exploitable vulnerabilities in a public issue. Use GitHub's private vulnerability reporting for this repository. Include the affected version, operating system, reproduction steps, and impact. Do not attach device data, pairing codes, credentials, or raw payloads unless strictly necessary; redact them first.

## Security behavior

- Hardware writes, command execution, pairing, connection setup, and interface opening are denied unless explicitly allowed by an exact local policy rule.
- The operating system remains the ultimate permission boundary.
- Raw communication payloads are excluded from local history by default; retention is configurable.
- Device-provided names, advertisements, descriptors, and payloads are untrusted input.
- MCP tool annotations describe behavior but do not grant or enforce permission.

## Scope and limitations

This project is pre-1.0 and has not received an independent security audit. A local policy allow rule is a standing permission; it is not an interactive per-call human confirmation. Hardware behavior varies by adapter, driver, operating system, and device firmware. Do not use experimental commands on safety-critical or production equipment.
