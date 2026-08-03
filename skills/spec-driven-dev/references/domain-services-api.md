# Services and API Adapter

Apply this adapter to backend services, APIs, events, and service-to-service integrations. Add requirements; never lower core gates.

Specify when applicable:

- request/response/event schemas, pagination, versioning, and compatibility policy;
- authentication, authorization, tenant/data boundaries, validation, and rate limits;
- error taxonomy, retry, timeout, cancellation, idempotency, and concurrency;
- persistence/transaction boundaries and consistency model;
- dependency degradation, observability, SLOs, rollout, and rollback.

Verify with:

- unit/property tests for deterministic domain rules;
- contract and integration tests against realistic dependency versions;
- an actually started service and real requests for success, validation, authorization, dependency failure, timeout, retry, and duplicate/idempotent behavior;
- database/state inspection where safe and applicable;
- sanitized logs, metrics, traces, and performance measurements.

Never expose secrets, private payloads, or production personal data in evidence. Record safe environment and version details, command working directory, process/port cleanup, and external operation IDs.
