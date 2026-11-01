# Universal Device MCP 2.0 — Complete product specification

Status: **V2 foundation implemented; not a complete V2 release**.

The current code adds a configured read-only hub for parallel inventory and reads from authenticated HTTP nodes. It is an initial distributed foundation and does not satisfy the full V2 target below. Missing release blockers include multi-tenant identity/authorization, node enrollment and revocation, mTLS or managed OAuth, persistent central inventory/job storage, offline synchronization, workflows/queueing, fleet observability, web console/API/CLI/SDK, signed upgrades, and measured fleet capacity. Do not describe the repository as a complete V2 platform until those requirements and the mandatory V1 gates have evidence.

V2 is the final distributed product and includes the entire V1 local-device feature set as its node runtime. The V1 acceptance requirements in [PRODUCT_V1.md](PRODUCT_V1.md) remain mandatory gates inside this V2 release; V1 is not a prerequisite release that the user must install separately. A node remains the only component that directly controls its attached hardware. The hub coordinates authorized nodes; it does not bypass device permissions, transport drivers or node-local policy.

## Product promise

An authorized operator can see a central inventory of devices attached to multiple UDMCP nodes, select nodes/devices by explicit scope, run bounded and auditable workflows across them, and recover useful status when a node or network is unavailable. Data and actions are isolated by organization and user policy.

“Thousands of devices” is a tested capacity target, not a guarantee. Support limits must be measured on a published reference configuration.

## V2 subsystems

### 1. Node agent

- Runs beside the V1 local MCP node and reports health, supported transports, software version, capabilities and device inventory.
- Uses outbound enrollment to a configured hub or mutually authenticated TLS to a configured endpoint; never opens a public unauthenticated listener by default.
- Maintains a unique node identity, revocable credentials, heartbeat, reconnect backoff, offline queue bounds and signed upgrade metadata.
- Preserves local policy as the final enforcement point. A hub request cannot grant permissions that the local owner has not granted.
- Accepts only requests addressed to an authenticated organization/node/device and provides idempotency keys for retryable jobs.

### 2. Central control plane

- Node registry with enrollment, ownership, status, last-seen time, capabilities and explicit revocation.
- Device inventory keyed by `(organization, node_id, local_device_id)`; never merge identical serial/model values across nodes without a validated identity proof.
- Search, groups and campaigns scoped to an organization, node, transport, model, tags and connectivity state.
- Workflow scheduler with a bounded job queue, concurrency quotas, deadlines, cancellation, retries only for idempotent operations, and per-target partial results.
- Event stream for connect/disconnect, task lifecycle, policy rejection, adapter failure and node state changes.
- Central audit records with actor, organization, node/device target, policy decision, request hash, result summary, timestamps and correlation ID. Raw hardware payloads stay opt-in and separately retained.

### 3. Identity and authorization

- Integrate with an external OIDC/OAuth 2.1 identity provider; V2 does not invent a password system or issue insecure static user tokens.
- Use short-lived access tokens, audience/resource validation, least-privilege scopes and server-side authorization for every request.
- Require organization membership and role checks for inventory, workflow, policy, user, node and audit operations.
- Support node-specific credentials and rotation/revocation. Secrets are stored in an OS secret store or managed secret service, never in source control or plain export files.
- Enforce TLS on all network paths, prefer mTLS for node-to-hub identity, and document certificate renewal, proxy trust and key compromise recovery.
- Record authorization decisions and deny cross-tenant resource IDs even if a caller guesses them.

### 4. Multi-tenant data model and persistence

- Central relational database for organizations, users/roles, nodes, device snapshots, groups, workflows, jobs, events, audit metadata and versioned policies.
- Tenant keys are part of all relevant unique indexes and query predicates.
- Use migrations, point-in-time backup/restore, retention, data export/deletion and documented disaster recovery.
- Queue/event delivery is at-least-once; consumers deduplicate with stable event IDs. Jobs expose pending/running/succeeded/partial/failed/cancelled/expired states.
- Keep high-volume telemetry and raw samples in a separate storage/retention path with explicit owner configuration.

### 5. Offline and synchronization behavior

- Nodes cache only policy-permitted inventory metadata and bounded events while disconnected.
- Synchronize with sequence numbers, conflict rules, schema versions and idempotency keys.
- Central policy revocations and expired approvals fail closed after reconnection; stale queued writes must never execute automatically.
- Queued work is classified as safe read, retryable idempotent action, or non-retryable mutation. Mutations require fresh online authorization and approval at execution time.
- Surface last successful synchronization, backlog size, dropped-event counts and conflicts.

### 6. Web console, API, CLI and SDK

- Web console for organization/user administration, node enrollment/revocation, device inventory, groups, approved workflows, audit review, health and retention controls.
- Versioned HTTP API with OpenAPI, OAuth scopes, pagination, filters, rate limits and stable error envelopes.
- CLI and Python SDK use the same API and authorization rules; they do not connect directly to remote hardware.
- Console output treats device strings as untrusted text and never renders them as HTML or executable markup.
- User interfaces show the precise node/device set, operation, payload hash, policy and expected partial-failure behavior before approval.

### 7. Protocol and adapter governance

- Signed or verified adapter package metadata, pinned versions, compatibility ranges and deprecation policy.
- Central protocol knowledge stores provenance, confidence, adapter version and supported firmware/device ranges.
- Device-supplied documents and data remain untrusted until reviewed; no agent-generated protocol can be globally published as confirmed without validation.
- Nodes advertise capability versions; the hub schedules only operations supported by that specific node build.

### 8. Observability and operations

- OpenTelemetry traces and metrics with correlation IDs across hub, queues and nodes; never emit secrets or raw device payloads by default.
- Metrics for node liveness, task latency, queue depth, adapter errors, policy denials, synchronization lag and fleet size.
- Structured logs with retention, access control, redaction and export.
- Alerts for node offline thresholds, repeated errors, queue saturation, certificate expiry, failed upgrades and backup failures.
- Operational runbooks cover incident response, revocation, restore, upgrade rollback and data-subject deletion.

### 9. Secure updates and deployment

- Reproducible, signed node and hub artifacts; software bill of materials and vulnerability scanning.
- Staged rollout by organization/node cohort, health checks, automatic halt and tested rollback.
- Infrastructure deployment guide for single-site and multi-site installations, trusted proxy/TLS topology, database/queue sizing and backup.
- No silent adapter auto-update that could change physical-device behavior. Updates are pinned, reviewable and controllable by node owners.

## V2 phases and exit conditions

| Phase | Work | Exit condition |
| --- | --- | --- |
| A — Architecture and threat model | Trust boundaries, data flows, abuse cases, identity design, capacity targets | Reviewed threat model and signed architecture decision records. |
| B — Node identity | Enrollment, keys, heartbeat, revocation, TLS/mTLS | Invalid/revoked nodes are rejected; keys rotate; no public unauthenticated listener. |
| C — Hub inventory | Tenant model, schema, migrations, inventory API | Cross-tenant isolation tests pass for every read/write endpoint. |
| D — Remote command plane | Jobs, queues, deadlines, cancellation, idempotency, partial results | Duplicate delivery and network loss cannot repeat mutations or hide partial outcomes. |
| E — Identity and policy | OIDC/OAuth, role/scope checks, local policy handoff, approval records | Independent authorization tests cover users, nodes, organizations and resource ownership. |
| F — Groups and campaigns | Dynamic groups, immutable target snapshots, quotas and workflows | Thousand-target simulator tests preserve target identity and bounded concurrency. |
| G — Offline sync | Event cursor, conflict resolution, bounded queue, stale-write rejection | Disconnect/reconnect simulations prove no stale mutation runs without current approval. |
| H — Console/API/SDK | Management UI, OpenAPI, CLI and Python client | Accessibility, authorization, pagination, injection and compatibility suites pass. |
| I — Observability and operations | OpenTelemetry, dashboards, alerts, runbooks, backup/restore | Load tests meet published SLOs; restore and incident exercises pass. |
| J — Supply chain and release | Signed artifacts, SBOM, scanning, staged updates, rollback | Signature verification and rollback pass on every supported node OS. |
| K — Scale and resilience | Multi-site load, queue saturation, node churn, partial outages | Measured fleet limits and recovery objectives are published and repeatable. |
| L — Security review | Independent penetration test, dependency audit and fixes | No unresolved critical/high findings; residual risks are published. |
| M — Pilot | Limited opt-in organizations, telemetry review, migration and support | Pilot acceptance criteria are met without unplanned data loss or unsafe action. |
| N — 2.0 release | Versioned APIs, deployment docs, migration, support and incident plans | All mandatory gates are green and operators can deploy/restore from documentation alone. |

## V2 release checklist

- [ ] All V1 acceptance requirements are implemented and validated as part of the V2 release.
- [ ] Threat model, privacy impact, retention, data ownership and incident response are reviewed.
- [ ] OIDC/OAuth integration and node mTLS work with at least two supported identity-provider configurations.
- [ ] Organization isolation and node/device ownership have exhaustive negative tests.
- [ ] Revocation, key rotation and lost-node recovery are documented and tested.
- [ ] Workflows handle retries, duplicate events, deadlines, cancellation and partial completion safely.
- [ ] Mutations require both current node-local permission and server-side authorized workflow approval.
- [ ] Offline queues never execute stale or expired mutations after reconnection.
- [ ] Thousand-node/device load targets, concurrency ceilings and SLOs are measured and documented.
- [ ] Console, API, CLI and SDK share authorization, audit and pagination semantics.
- [ ] OpenTelemetry, dashboards, alerts, backup/restore and rollback are tested.
- [ ] Releases are signed, have an SBOM, and support staged rollout and rollback.
- [ ] Independent security review is complete and material findings are fixed.
- [ ] Pilot users validate installation, upgrades, support and data export/deletion before general availability.

## Explicit V2 non-promises

Capacity, adapter coverage, cross-site reachability and workflow completion depend on real networks, host permissions, node health and hardware. A hub can report partial completion; it cannot make independent physical devices transactional. V2 does not bypass pairing, firmware protections, user consent or local operating-system permission boundaries.
