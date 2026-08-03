# Artifact Contract

## Contents

- [Initiative root](#initiative-root)
- [Profile layouts](#profile-layouts)
- [Stable identifiers](#stable-identifiers)
- [Workflow state](#workflow-state)
- [Confirmation records](#confirmation-records)
- [Evidence records](#evidence-records)
- [Review and revision records](#review-and-revision-records)
- [Template usage](#template-usage)
- [Scaffolding](#scaffolding)
- [Validation](#validation)

## Initiative Root

Prefer the repository's existing feature-spec convention. Otherwise use:

```text
docs/specs/<initiative>/
```

Record the chosen path in `workflow-state.md`. Never reuse one initiative directory for unrelated work or overwrite an existing artifact to force it into the template.

## Profile Layouts

Lite:

```text
<initiative>/
├── workflow-state.md
├── change.md
├── amendments/
├── spikes/
└── reviews/
    ├── code-review-M1.md
    └── acceptance.md
```

Standard:

```text
<initiative>/
├── workflow-state.md
├── requirements.md
├── spec.md
├── spikes/
├── amendments/
├── plans/
│   └── M1-plan.md
└── reviews/
    ├── spec-review.md
    ├── plan-review-M1.md
    ├── code-review-M1.md
    └── acceptance.md
```

High-assurance always adds `release-plan.md`; any profile targeting `release-ready` or `deployed` adds it as well. For an `implemented` High-assurance target, use the file to state release/deployment non-scope and applicable future safeguards without requiring production authority. Add any repository-required threat model, privacy assessment, migration runbook, or recovery artifact. Keep profile-specific details in the appropriate existing artifact instead of creating empty files for every possible risk.

## Stable Identifiers

Use zero-padded, initiative-local IDs:

| Kind | Pattern | Meaning |
|---|---|---|
| Requirement | `REQ-001` | Confirmed intent or constraint |
| Risk | `RISK-001` | Material uncertainty or harm |
| Spike | `SPIKE-001` | Time-boxed question/evidence |
| Decision | `DEC-001` | Chosen/rejected technical option |
| Acceptance | `AC-001` | Verifiable contract outcome |
| Phase | `PHASE-M1-001` | Ordered implementation chunk with a human gate |
| Task | `TASK-M1-001` | Milestone-owned execution unit |
| Evidence | `EVID-001` | One reproducible verification record |
| Amendment | `AMD-001` | Versioned contract delta |

Define IDs in Markdown headings exactly, for example:

```markdown
## REQ-001 — Preserve existing user data
### PHASE-M1-001 — Migration safety slice
### TASK-M1-001 — Add migration guard
### EVID-001 — Migration dry run
```

Reference IDs inline without redefining them. Never recycle a retired ID; preserve it with a status and create a new one.

Maintain this chain where applicable:

```text
REQ/RISK → SPIKE/DEC → AC → PHASE → TASK → EVID → phase review → milestone acceptance
```

Every `AC-*` names at least one `REQ-*`. Every phase names its owned ACs and tasks. Every task names exactly one phase and its owned ACs. Every evidence record names its task and ACs.

Every phase carries a human review contract and operational verdict:

```markdown
- Status: pending | executing | verifying | awaiting-human-review | approved | rejected | reopened
- Sequence: <positive integer>
- Depends on: <prior PHASE IDs or none>
- Goal: <independently observable outcome>
- Acceptance: <AC IDs>
- Tasks: <TASK IDs>
- Verification checkpoint: <commands/interactions and passing condition>
- Checkpoint revision: <exact aggregate phase revision or pending>
- Human review procedure: <reproducible steps and artifacts to inspect>
- Human review status: pending | approved | rejected | invalidated
- Human reviewer: <person/role or none>
- Human reviewed at: <ISO-8601 or none>
- Human review revision: <exact Checkpoint revision or pending>
- Human review evidence: <current passing EVID IDs or pending>
- Human review note: <verdict/feedback or pending>
```

The phase structure, checkpoint procedure, and human review procedure are normative plan content. Status, checkpoint revision, and verdict fields are mutable operational state. Only `approved` with a concrete human, timestamp, `Human review revision` equal to the exact frozen `Checkpoint revision`, current passing evidence covering every phase task, and a verdict note unlocks later phases. Later milestone reconciliation may update evidence candidate mappings without rewriting the preserved phase checkpoint revision.

## Workflow State

Keep exact top-level fields so the validator and a resumed agent can reconstruct state:

```markdown
- Run ID: SDD-...
- Artifact root: docs/specs/example
- Rigor: lite | standard | high-assurance
- Commit policy: auto | checkpoint | user-managed
- Delivery target: implemented | release-ready | deployed
- Workflow status: <state>
- Technical options status: unassessed | awaiting-confirmation | confirmed | not-applicable
- Current milestone: M1
- Current phase: PHASE-M1-001 | none
- Current task: TASK-M1-001 | none
- Base revision: <sha/digest/unversioned/git:unborn>
- Initial dirty paths: <paths/none>
- Initial staged paths: <paths/none>
- Owned paths: <project-relative paths/none>
- Last checkpoint: <ISO-8601 or none>
- Next safe action: <one concrete action>
- Review mode: independent | degraded | blocked | unassessed
```

Also maintain capability/authority, active resources, external-operation records, retry/diagnostic history, owned paths, and cleanup state. Do not store credentials or secret values.

## Confirmation Records

Use explicit fields after confirmation:

```markdown
- Requirements status: confirmed
- Confirmed by: user
- Confirmed at: 2026-08-03T12:00:00+08:00
- Confirmed revision: sha256:...
```

For significant decisions use the same confirmation fields inside each `DEC-*` block. Before confirmation, use `draft` or `awaiting-confirmation` and `none` for confirmation metadata.

Confirmation revisions bind canonical payloads, not mutable whole files:

- A requirements payload contains the goal, non-goals, and ordered `REQ-*` statements/constraints; it excludes confirmation metadata and task/runtime state.
- A significant-decision payload contains the DEC ID, linked requirements/risks, chosen option, benefits/costs, operational/migration/lock-in consequences, and rejected alternatives; it excludes confirmation metadata and unrelated later specification prose.

Use `validate_traceability.py --print-digests` to produce the canonical `sha256:` values. It strips inactive fenced examples and HTML comments, normalizes LF line endings and trailing whitespace, and projects:

- Standard/High-assurance requirements as the requirements document without confirmation-control fields;
- Lite requirements as `Goal and Non-Goals` plus ordered `REQ-*` blocks;
- each decision without status/confirmation-control fields, plus an ordered aggregate for significant options;
- the specification without status/input-binding/option-confirmation fields;
- each milestone's normative plan fields while excluding phase/task status, phase human-verdict metadata, task blockers/resume conditions, execution checkboxes, and actual revision mappings.

Review digests are transitive. A specification review binds the canonical requirements digest plus the specification projection. A plan review binds requirements, the specification when present, and that milestone's normative plan projection. A code review binds all of those inputs plus the milestone candidate revision recorded in the plan. This means updating a self-reported revision field cannot preserve an old review after its real upstream input changes.

Record the emitted requirement digest in `Confirmed revision`, each decision digest in its `Confirmed revision`, the significant-options aggregate in `Options confirmed revision`, the specification digest in each plan's `Spec revision`, and the applicable review digest in `Input contract digest`. Editing a canonical payload field, linked confirmed requirement, or reviewed candidate changes the emitted digest, invalidates the gate, and requires amendment/reconfirmation or re-review. Later prose may evolve only when it is outside the relevant canonical projection. Mirror the aggregate gate in `Technical options status`: `confirmed` when significant decisions exist and are confirmed, otherwise `not-applicable`.

## Evidence Records

Use one `### EVID-*` block per verification result. Keep result and freshness separate:

```markdown
### EVID-001 — Existing data survives migration

- Acceptance: AC-001
- Task: TASK-M1-001
- Outcome: passed
- Freshness: current
- Blocker: none
- Verification class: migration
- Subject revision: sha256:<digest of covered implementation/config/dependency paths>
- Candidate mapping: sha256:<accepted candidate revision after reconciliation>
- Recorded at: 2026-08-03T12:34:56+08:00
- Environment: macOS; Python 3.13; local fixture database
- Method: `python -m pytest tests/test_migration.py`
- Exit code: 0
- Expected: Existing rows remain unchanged and new fields receive defaults.
- Actual: 24/24 fixture rows preserved; defaults populated.
- Artifacts: `artifacts/migration-report.json` (sha256:...)
- Sanitization: No credentials or personal data recorded.
- Cleanup: Temporary database removed; no active process.
- Invalidation: stale when migration code, schema, fixture, database version, or AC-001 changes.
- Authorization: not-applicable
- Risk scope: not-applicable
- Risk impact: not-applicable
- Risk owner: not-applicable
- Risk expiry/revisit: not-applicable
```

Do not make an evidence file hash or future commit SHA refer to itself. Compute `Subject revision` from the covered implementation/configuration/dependency paths while excluding workflow state and evidence files. When the covered code already has an immutable commit, `git:<sha>` is also valid. During reconciliation and milestone acceptance, set `Candidate mapping` to the exact accepted candidate revision without replacing the original covered-path subject. Release/smoke evidence additionally uses the observed deployed revision as its subject.

Record command working directory when it is not obvious. For browser/device/manual observation, replace the command with the exact interaction procedure and record expected/actual observations. For performance, record warm-up, sample size, hardware/runtime, and threshold. For external operations, record the operation ID and queried result.

Store large logs, screenshots, traces, and reports under the initiative's `artifacts/` directory; record a short summary, initiative-relative path, and SHA-256. Redact credentials, tokens, personal data, private endpoints, and unnecessary production content. Record cleanup of services, ports, devices, temp files, and test data.

Use `not-applicable` only with a reason; it remains visible and does not satisfy an AC/task by itself. Use `accepted-risk` only with explicit authorization, exact scope, impact, owner, and expiration/revisit condition. Mark covered evidence stale when inputs change; never rewrite a failed result as passed without a new evidence record.

## Review and Revision Records

Every milestone plan (including Lite's combined `change.md`) and acceptance record maintains:

```markdown
- Base revision: <sha/digest/unversioned/git:unborn>
- Candidate revision: <sha/digest or pending>
- Reviewed revision: <sha/digest or pending>
- Accepted revision: <sha/digest or pending>
- Release revision: <sha/digest or not-applicable>
- Deployed revision: <sha/digest or not-applicable>
```

Plans describe how the final revision will be pinned; they do not predict a future SHA. Acceptance fills actual values.

Every review record includes:

- review kind and profile;
- reviewer/context identity and isolation method;
- input artifacts and revisions/digests, including one `Input contract digest` for the frozen normative projection;
- relevant source/manifests/ADRs/evidence inspected;
- repository fingerprint before and after;
- blocking/important/minor findings and closure state;
- status `draft`, `independent-passed`, `degraded-reviewed`, `blocked`, `stale`, or `superseded`;
- residual limitations.

For a code review, both repository fingerprints must equal the exact candidate revision for that milestone; equal-but-unrelated fingerprints do not establish which candidate was reviewed. When a milestone spans multiple plan files, they must all record the same candidate revision.

Freeze normative contracts, not live bookkeeping. The normative plan projection contains milestone goal/constraints; each phase's ID, sequence, dependencies, goal, AC/task ownership, verification checkpoint procedure, and human review procedure; and each task's ID, phase, acceptance ownership, dependencies, owned paths/change/interface scope, verification and effect checks, evidence method, side-effect/idempotency, cleanup, invalidation, and commit/checkpoint rule. Mutable operational fields are task/phase `Status`, task blockers/resume conditions, phase checkpoint revision and human review status/reviewer/time/revision/evidence/note, execution checkboxes, diagnostic/history entries, and actual candidate/reviewed/accepted/release/deployed revisions. `workflow-state.md` is mutable control state and is never part of a normative contract digest. Lite applies the same section-scoped rule inside `change.md`: requirements confirmation binds only its requirements payload, and code/plan review binds only the normative milestone/phase/task projection.

Operational updates do not invalidate a review. Any normative-field change requires an `AMD-*`, marks the active review `stale`, and creates a replacement review. Preserve the prior record under `reviews/history/<gate>-r<n>.md` with `Status: superseded` and reciprocal `Supersedes`/`Superseded by` links; keep the current active record at the canonical path such as `reviews/plan-review-M2.md`. Strict validation considers the canonical active records and rejects stale/superseded active gates.

Use `Spec status: reviewed` after the specification review passes. Use plan states `draft → awaiting-review → reviewed → accepted`; set `accepted` only after its candidate, evidence, and milestone acceptance reconcile. Strict delivery requires a reviewed specification and accepted plans.

## Deployment Operation Contract

For a `deployed` target, `release-plan.md` must record `Release authority` as `principal=<approving person/role>; approval=<immutable approval or change-request ID>`, for example `principal=release-manager; approval=CHG-1042`. A bare `yes`, `authorized`, or role without an approval reference is not concrete authority. Every current passing release/smoke `EVID-*` record must copy the exact full value into `Authorization`; `not-applicable`, `pending`, or an unrelated approval is invalid.

The `workflow-state.md` external-operation ledger is mandatory for deployed delivery. Its header is:

```markdown
| Operation ID / idempotency key | Target and intended effect | Subject revision | Pre-state | Rollback/recovery | State | Recovery query | Result evidence |
```

Before execution, persist a concrete operation/idempotency ID, exact target and effect, subject revision, observed pre-state, rollback or recovery procedure, and a query that can reconcile the operation after interruption. Every ledger row must use a valid exact subject revision, contain no placeholder cells, and use `prepared`, `observed`, `rolled-back`, `cancelled`, `unknown`, `blocked-permission`, or `blocked-external`. A successful deployed claim requires exactly one ledger section containing exactly one table and at least one `observed` row whose subject equals `Deployed revision` and whose result references current passing release evidence. No operation may remain `prepared`, `unknown`, or `blocked-*`; query and reconcile it before delivery.

## Template Usage

Use the bundled files in `assets/templates/`:

- `workflow-state.md` for resumable control state;
- `change.md` for Lite's combined contract and plan;
- `requirements.md`, `spec.md`, and `milestone-plan.md` for Standard/High-assurance;
- `spike.md` for pre-spec or tactical questions;
- `amendment.md` for every contract delta;
- `review.md` for spec, plan, and code reviews;
- `acceptance.md` for evidence and milestone baselines;
- `release-plan.md` for every `release-ready` or `deployed` target and for High-assurance release/rollback analysis.

Delete instructional placeholders only when replacing them with real content. Do not retain a fake `REQ-001`, `AC-001`, task, or evidence entry that does not describe the initiative.

## Scaffolding

Run from the installed skill directory or use an absolute script path:

```bash
python3 <skill-root>/scripts/scaffold_artifacts.py /path/to/project initiative-slug \
  --profile standard \
  --commit-policy user-managed \
  --delivery-target implemented
```

The scaffold command:

- derives `docs/specs/<initiative>/` unless `--artifact-root` is provided;
- captures the current Git base and dirty paths without modifying them;
- creates only profile-relevant artifacts;
- refuses a non-empty target by default;
- uses `--merge` only to add missing files without overwriting any file;
- supports `--dry-run` for inspection.

Inspect every generated path and replace placeholders before treating artifacts as authoritative.

## Validation

Run structural validation during authoring:

```bash
python3 <skill-root>/scripts/validate_traceability.py docs/specs/<initiative>
```

Print canonical digests before recording a confirmation or review, and again after any suspected normative change:

```bash
python3 <skill-root>/scripts/validate_traceability.py docs/specs/<initiative> --print-digests
```

Run strict validation before claiming the delivery target:

```bash
python3 <skill-root>/scripts/validate_traceability.py docs/specs/<initiative> --strict
```

Strict mode recomputes transitive confirmation/review digests and rejects an empty or broken `REQ → AC → PHASE → TASK → EVID` chain, phases without matching explicit human approval, unconfirmed significant decisions, draft specs/plans, missing milestone-specific plan/review gates, code-review fingerprints that differ from the milestone candidate, duplicate authoritative fields, contradictory blockers, stale/non-passing evidence, broken adjacent-milestone revision continuity, mismatched workflow/plan/acceptance/release/deployed revisions, and deployed claims without matching authority, release evidence, or a reconciled operation ledger. It recognizes active CommonMark headings and fields with up to three leading spaces, opens Markdown without following symlinks, and redacts detected credential forms from diagnostics. The validator proves artifact consistency only; it does not prove that a recorded reviewer was human or replace the recorded runtime, security, review, or deployment evidence.

The validator checks profile layout, stable definitions, duplicate IDs, AC→REQ links, PHASE→TASK/AC links, TASK→PHASE/AC links, EVID→TASK/AC links, required evidence fields, task/evidence status consistency, per-phase human review metadata and evidence/revision binding, review status, confirmation fields, unresolved placeholders, and common secret patterns. It cannot prove behavior, correctness, reviewer identity, security, independence, or deployment. Treat its success only as traceability evidence.
