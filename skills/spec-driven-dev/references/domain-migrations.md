# Migration Adapter

Apply this adapter to schema, data, storage, protocol, configuration-state, or format migrations. Use at least Standard for a reversible non-production migration. Treat destructive/irreversible data work, sensitive or regulated data, and production migrations as High-assurance.

Specify:

- source/target schemas and invariants;
- compatibility window and forward/backward readers;
- volume, ordering, concurrency, resumability, idempotency, and partial-failure recovery;
- backup, audit, reconciliation, rollback/restore, and retention behavior;
- exact environments/targets, authority, and blast radius.

Before real execution, verify representative dry runs, integrity invariants, counts/checksums, semantic samples, compatibility, performance/resource bounds, and rollback or restore rehearsal.

Write a durable intent and idempotency/resume record before mutation. If an operation is interrupted or its outcome is unknown, query actual state using the operation ID before any retry. Never replay a migration merely because local task state or Git is incomplete.
