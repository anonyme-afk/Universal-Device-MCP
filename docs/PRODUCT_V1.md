# Universal Device MCP 1.0 — Product and release specification

Status: **target definition; not a claim that 1.0 is complete**.

V1 covers one computer, its locally attached or reachable devices, and one local MCP process. V2 adds multiple computers and a central control plane. Do not make V1 depend on the V2 service.

## Product promise

An MCP client can discover devices exposed by supported host adapters, tell identical units apart when the host provides stable evidence, inspect observed interfaces, perform documented or explicitly permitted operations, save local knowledge, and continue working with several devices concurrently. The server reports uncertainty and adapter limitations instead of inventing protocol knowledge.

“Universal” describes the extensible adapter architecture. It is not a guarantee that all existing or future devices can be recognized or controlled.

## Local access modes and media capture

The owner-selected `UDMCP_ACCESS_MODE` supports `safe` (default, exact allowlist for mutations), `trusted` (configured exact device IDs/fingerprints plus an operation allowlist), and `full` (supported non-critical operations without per-operation rules). Selection is made in the local server environment and cannot be changed by an MCP tool. Explicit policy denies, the OS, adapter constraints and write-size limits apply in every mode. Firmware flashing, erase/wipe/format, delete/remove, arbitrary execute, factory reset and bootloader unlock remain blocked in every mode.

Optional camera/audio support uses OpenCV and sounddevice. Capture requires owner configuration `UDMCP_MEDIA_CAPTURE=true` and an explicit tool call. The current release provides bounded single-frame JPEG capture and at most 10 seconds of in-memory WAV capture; it does not provide continuous streams, adjustable camera controls, transcription or image analysis. Captures are not retained on disk.

## Supported local scope

| Transport | V1 support claim | Conditions and exclusions |
| --- | --- | --- |
| USB | Enumerate devices, descriptors, configurations, interfaces and endpoints; generic bulk/interrupt/control I/O | PyUSB, libusb/backend, driver ownership and OS permissions apply. Never merge same-VID/PID devices without distinguishing identity evidence. |
| USB HID | Enumerate and perform generic report I/O | OS access rights and report layout apply; descriptor interpretation must be documented before claiming semantic controls. |
| Serial/UART | Enumerate ports and generic read/write with explicit settings | Port drivers, permissions, and device protocol apply. |
| BLE | Scan and inspect GATT services/characteristics; generic characteristic reads/writes | Bluetooth hardware, OS permissions and pairing apply. Bluetooth Classic is excluded unless a separately tested adapter is added. |
| Local network | Discover advertised mDNS/DNS-SD TCP/UDP services and communicate with the exact discovered endpoint | No unrestricted address/port scan. Network writes require policy authorization. |
| Android | USB ADB discovery, properties/inspection, argv-based shell; wireless debugging through advertised pairing/connect services | ADB installation, owner authorization and Android shell permissions apply. |
| iOS/iPadOS | USB/usbmux discovery, best-effort descriptors, trusted-device inspection, paired Bonjour discovery, pinned `pymobiledevice3` argv | Apple host support, unlock/trust/pairing and iOS service availability apply. Passcode/trust bypass and arbitrary shell are explicitly excluded. |
| Simulator | Ten deterministic same-model virtual devices for demonstrations and tests | Simulator results are marked as simulated and never claim physical hardware access. |

Every adapter must independently report missing dependencies, permission errors, timeouts, malformed descriptors and unsupported operations. One adapter failure must not erase successful results from others.

## Required behavior

### Discovery and identity

- Run available adapter discovery concurrently with a bounded worker pool.
- Record connect, disconnect, state and stable-configuration changes without treating runtime addresses or authorization state as hardware reconfiguration.
- Return a stable internal ID and explain the identity basis (serial, UDID, topology, or unstable host address).
- Distinguish same-model units; where the host cannot identify a unique unit, reject control and ask for a fresh discovery instead of guessing.
- Preserve successful adapter results when another adapter fails.

### Inspection and capability knowledge

- Keep observed facts, documented capabilities, confirmed discoveries and hypotheses distinct.
- Associate discoveries with device, source, confidence and timestamp.
- Provide an inventory summary, interface explanation, capability view, diagnostics, payload analysis and exportable device report.
- Do not infer that a response means an undocumented command is understood.
- Treat all names, descriptors, advertisements, payloads and device-originated text as untrusted data.

### Communication and orchestration

- Preserve generic transport primitives rather than building a closed catalog of product-specific actions.
- Expose transport-specific options and hex payloads with validation, bounds, timeouts, exact target checks and clear adapter errors.
- Support concurrent reads across explicitly named targets, up to the documented bound, with one independent result per device/interface pair.
- Resolve dynamic groups from exact IDs and documented metadata criteria; report matches and connection state before group operations.
- Group reads use immutable resolved target lists and independent per-device results. Group writes require a frozen target plan, exact local policy authorization for every target, MCP elicitation approval, a short expiry, one-time replay protection, and per-target partial-failure reporting. Never claim a group write is atomic.
- A workflow must identify its sequence, target set, expected outputs, timeout and cancellation behavior. Unknown or destructive steps are rejected unless a future validated approval design explicitly permits them.

### Security and privacy

- Default deny hardware mutation, command execution, pairing/connection setup and interface opening.
- Allow only exact local rules by transport, device identity, interface and operation; explicit denies win. Enforce at the server boundary, not only through MCP annotations.
- Bound payload size, concurrent sessions, request duration and batch size. Respect host OS/driver permissions.
- Never let device-discovered text authorize an action or provide instructions to the model.
- Do not store raw request/response payloads by default. Redact credentials, document local storage, and provide configurable retention and explicit profile/history deletion.
- Automatic monitoring is off unless the owner enables it.
- Local allow rules are standing permission, not per-request human confirmation. Documentation must say so.

### Local memory

- Keep per-device profiles in the user's local SQLite data directory.
- Migrate schema without discarding existing profiles.
- Preserve identity, hardware, interface, protocol, capability, discovery, experiment and history metadata with appropriate confidence and retention.
- Reuse profiles after reconnect and snapshot stable configuration changes.
- Support inventory and profile export, per-device deletion, and a documented full local-data reset procedure.

### MCP and distribution

- Require Python 3.11+ and the official Python MCP SDK v2. Support its current 2026-07-28 protocol behavior and legacy protocol negotiation; do not carry a handwritten protocol runtime.
- Use stdio for local desktop clients. Advertise Streamable HTTP only when authenticated, TLS-terminated and documented for a remote deployment.
- Test discovery, schemas, resources, error results and supported transport behavior with official MCP Inspector CLI in CI.
- Publish a tested package, pinned release metadata, `server.json`, changelog, security policy, contribution guide and copyable configurations for the clients actually validated.
- Do not call a GitHub push, registry entry or PyPI upload a technical certification.

## V1 phases and completion gates

| Phase | Deliverables | Exit condition |
| --- | --- | --- |
| A — Core and identity | Adapter contract, profile schema, stable IDs, isolated errors | Duplicate-device and adapter-failure tests pass on all supported OS/Python jobs. |
| B — Adapters | USB, HID, Serial, BLE, mDNS network, Android ADB, iOS and simulator | Each advertised capability has tests and an OS prerequisite matrix; unsupported cases are stated. |
| C — Safe communication | Generic I/O, limits, timeout handling, sessions, default-deny policy | No mutating tool reaches a fake adapter without an exact allow rule; per-target failures are observable. |
| D — Memory and privacy | Migrations, profiles, confidence, payload redaction, retention, export/deletion | Restart/reconnect, retention and deletion tests pass without losing retained profiles. |
| E — Multi-device | Parallel discovery/read, identical IDs, dynamic groups, diagnostics | Ten simulated identical devices return ten distinct results; one disconnect does not suppress other results. |
| F — MCP interoperability | Current SDK v2, stdio client samples, Inspector CLI | Inspector calls tools/resources on Linux, Windows and macOS. Legacy and current protocol paths are exercised. |
| G — Installation and docs | PyPI package, optional extras, OS/client instructions, `server.json` | Clean-machine install tests and package metadata checks pass; package is actually published before README calls it published. |
| H — Hardware validation | USB/serial/BLE/Android/iOS/network smoke matrix with fixture records | Every release claim is backed by a repeatable device/OS result or clearly marked unverified. |
| I — 1.0 release | Version/tag, artifacts, changelog, security contact, support policy | All mandatory gates above are green; no undocumented P0/P1 requirements remain. |

## V1 release checklist

- [ ] The complete matrix is published with tested OS, Python, transport and adapter-library versions.
- [ ] Linux, Windows and macOS CI passes at every supported Python version.
- [ ] The full software suite is deterministic and has no platform-specific unexplained failures.
- [ ] MCP Inspector CLI checks tool discovery and representative safe tool calls in CI.
- [ ] The ten-device simulator covers duplicate models, disconnects, adapter failures, policy denial and partial results.
- [ ] Security policy, retention, redaction, deletion and restart behavior have direct tests.
- [ ] All adapters have documented prerequisites and at least a mock-based test; physical hardware claims have a recorded smoke result.
- [ ] Package builds from a clean checkout and installs in a fresh environment on all supported OSes.
- [ ] Client snippets are tested against the named client versions.
- [ ] Release metadata and docs use the same version and make no unsupported compatibility promises.
- [ ] The public release is published and its installation path is verified from a clean machine.

## Explicitly outside V1

Central multi-computer inventory, cross-site orchestration, multi-organization access control, fleet campaigns, remote synchronization and the web administration console belong to V2. New device models and undocumented protocols are maintenance/extensions, not a promise of universal recognition.
