---
name: spec-driven-dev
description: "Use for greenfield products, cross-module features, risky small changes (authentication, security, migrations, data loss, external integrations, releases), or work explicitly requesting SOP/spec-driven/document-first development, autonomous verification, human-reviewed implementation phases, or evidence-backed delivery. Provides a risk-scaled pipeline with requirements and significant-option confirmation, pre-spec spikes, specifications, phased milestone plans, strongest-applicable verification, AI correction loops, mandatory per-phase human review, independent reviews, traceable evidence, and safe delivery. Do not use for low-risk trivial edits, pure refactors, or standalone research unless the user explicitly requests the workflow."
---

# Spec-Driven Development

Drive an initiative from intent to an evidence-backed delivery without confusing written code, passing unit tests, release readiness, and deployment. Scale ceremony to risk, preserve user-owned work, and keep every completion claim traceable to current evidence.

## Start Here

1. Read repository instructions and inspect the real code, scripts, docs, version-control state, and available tools before proposing a workflow.
2. Choose an initiative slug and use the repository's existing convention; otherwise isolate artifacts under `docs/specs/<initiative>/` so parallel initiatives cannot collide.
3. Read [rigor-profiles.md](references/rigor-profiles.md), choose `lite`, `standard`, or `high-assurance`, and record why. Escalate the profile whenever newly discovered risk exceeds it.
4. Read [artifact-contract.md](references/artifact-contract.md), then scaffold from the bundled templates. Do not overwrite existing artifacts.
5. Read [lifecycle-and-gates.md](references/lifecycle-and-gates.md) before changing production code. Read only the applicable adapters: [Web UI](references/domain-web-ui.md), [services/API](references/domain-services-api.md), [CLI/library](references/domain-cli-library.md), [data/ML](references/domain-data-ml.md), [migrations](references/domain-migrations.md), [infrastructure](references/domain-infrastructure.md), [mobile/desktop](references/domain-mobile-desktop.md), or [legacy/refactor](references/domain-legacy-refactor.md). Apply Data/ML to model or metric work even when delivered as a script; apply CLI/library only when its public invocation/package contract matters.

Prefer the bundled commands:

```bash
python3 <skill-root>/scripts/scaffold_artifacts.py <project-root> <initiative> --profile standard --commit-policy user-managed
python3 <skill-root>/scripts/validate_traceability.py <initiative-root>
python3 <skill-root>/scripts/validate_traceability.py <initiative-root> --print-digests
```

Adapt interpreter and paths to the environment. Inspect generated files before continuing. `--merge` may add missing files but never overwrite content.

## Non-Negotiable Invariants

- **Authority and scope:** obey platform constraints, current user instructions and confirmations, repository rules, requirements, spec, then plan. Stop and surface contradictions; never silently choose a lower-authority source.
- **User gates when applicable:** treat an explicit request as requirements confirmation when it already fixes scope, non-goals, and acceptance; otherwise obtain confirmation. Confirm every significant technical option. If none exists, record `not-applicable` without manufacturing choices or a second question. A significant option changes architecture, data ownership, authentication, public interfaces, core external integrations, deployment topology, migration/lock-in risk, or feasibility. For greenfield user interfaces, the UI foundation (reuse an existing design system, adopt a component library, or build with native/custom components) is always a user-confirmed option; never silently choose a library or silently default to custom components. Do not ask about reversible tactical choices inside confirmed boundaries.
- **Evidence-backed completion:** assign stable `REQ`, `DEC`, `AC`, `PHASE`, `TASK`, and `EVID` IDs. A task is complete only when its applicable criteria have current strongest-available evidence. Passing tests alone is insufficient when runtime, API, visual, performance, migration, or operational effects exist.
- **Human-reviewed implementation phases:** divide each milestone plan into ordered `PHASE-M<n>-*` chunks containing multiple tasks/steps. Put a phase boundary after each user-reviewable critical capability or small coherent capability group; do not hide all core flows inside one implementation phase. After AI completes every task and the phase checkpoint converges, set the phase to `awaiting-human-review`. Only explicit human approval may unlock the next phase; silence, requirements confirmation, AI/subagent review, or final milestone acceptance cannot substitute.
- **No invented tests:** use red-green TDD for suitable behavior, a failing reproduction for defects, contract/build checks for configuration, interaction or screenshot evidence for UI, dry runs for migrations, and explicit question/evidence for spikes and docs. Never manufacture a meaningless failing unit test.
- **No silent change:** if implementation contradicts a confirmed requirement, decision, spec, plan contract, or acceptance criterion, run the amendment protocol before affected implementation continues. Old review notes are never a substitute for reviewing the delta.
- **No false finish:** a task is `completed` only when its applicable criteria are current and passing; a phase is `approved` only after explicit human review of its checkpoint and evidence. Blocked, cancelled, stale, not-applicable, awaiting-human-review, and explicitly accepted-risk states remain visibly distinct.
- **No blind external retry:** before any non-idempotent external action, persist intent, operation ID/idempotency key, exact subject revision, pre-state, recovery procedure, expected effect, and recovery query. On resume, query state before retrying; a deployed claim requires a fully reconciled observed ledger entry.
- **No assumed Git authority:** commits are optional policy, not gates. Protect initial dirty paths and index entries, stage only safe owned hunks, inspect staged diffs, and never use bulk staging, amend, reset, or destructive cleanup unless explicitly authorized. Pre-existing staged content or overlap with user-edited files forces `user-managed` or an explicitly authorized isolated worktree.
- **No fake independence:** reviewers use a fresh isolated context with no author reasoning. Because filesystem read-only may be unenforceable, freeze and compare repository fingerprints and never run a writer concurrently with a reviewer. A code review's before/after fingerprints must both equal the milestone candidate.
- **Accurate delivery label:** report `implemented`, `release-ready`, or `deployed`. Say shipped/deployed only after the authorized deployment and post-deploy checks pass.

## Lifecycle

```text
Preflight → select rigor → frame requirements → user confirms requirements
→ pre-spec spikes for decision-blocking unknowns
→ user confirms significant options → specify → profile-required review
→ milestone plan → profile-required review
→ execute phase tasks {verify first → implement → effect check → fix ↺ → evidence}
→ phase checkpoint → human reviews phase {reject → reopen phase tasks ↺ | approve → next phase}
→ crash-reconcilable task finalization → code review {reopen task ↺}
→ milestone/full regression {reopen task ↺} → acceptance → deliver
```

### 0. Preflight

Persist `workflow-state.md` before implementation:

- run ID, initiative root, rigor and rationale;
- delivery target and explicit non-goals;
- current milestone, phase, task, and the latest phase-gate verdict;
- capabilities/authority for writes, network, dependency installation, browser/device, credentials, external APIs, production, deployment, and destructive actions;
- Git presence, branch, base revision, initial dirty paths, owned paths, and `commit_policy: auto | checkpoint | user-managed`;
- review availability, active resources, current state, retry/diagnostic count, blocker, and next safe action.

Default to `user-managed` commits unless the user or repository authorizes agent commits. Never touch production merely because local implementation is authorized.

### 1. Frame and Confirm Requirements

Explore only until the direction is clear. Write verifiable `REQ-*`, non-goals, risks, success measures, and candidate acceptance criteria. Mark the requirements `confirmed` only after an explicit confirmation, including an already-specific originating request when it fully supplies the contract; after—not before—the confirmation, record the source, time, and canonical digest emitted by `--print-digests`.

### 1.25. Resolve Decision-Blocking Unknowns

Run time-boxed pre-spec spikes under `spikes/SPIKE-*` before asking the user to choose an affected technical option. A spike answers one explicit question; it does not require TDD, and experiment code is disposable by default. Record commands, environment, outcome, confidence, artifacts/hashes, and decision impact. Remove experiment code before normal implementation; rewrite retained behavior through the planned verification flow.

### 1.5. Confirm Significant Technical Options

Present 2–3 viable options when they exist, compare evidence, costs, risks, lock-in, migration, and operations, recommend one, then ask for one consolidated confirmation round. For a greenfield Web/mobile/desktop UI, include a distinct UI-foundation decision covering existing design-system reuse, a named component library, or native/custom components; compare framework/version compatibility, accessibility maturity, theming, bundle/runtime cost, license, maintenance, and exit cost. Do not bury this choice inside the final specification after the confirmation gate. Record confirmed `DEC-*`, rejected alternatives, consequences, evidence, confirmer, time, and the emitted per-decision/aggregate digests. If no significant option exists, record the gate `not-applicable` and continue. If a significant option later changes, return through amendment and this gate.

### 2–3. Specify, Review, and Plan

Define technology-neutral behavior, state, interfaces, safety boundaries, failure behavior, milestones, and numbered `AC-*`. Map each AC to requirements. Keep one coherent plan per milestone, divide it into ordered `PHASE-M<n>-*` implementation chunks, and place multiple small `TASK-M<n>-*` tasks/steps inside each phase. Give every phase an independently observable checkpoint and human review procedure. For user-facing CRUD/product work, plan review must reject a single phase that bundles all independently reviewable create, edit, state-change, destructive, persistence, or recovery flows. Use vertical slices: the reviewer must be able to exercise the completed capability through the real UI/API before approving later work. Group only tightly coupled behaviors whose separate review would not produce a usable checkpoint. Destructive/data-loss, authentication/authorization, migration, payment, and external side-effect flows require their own human gate unless the user explicitly approves a documented grouping. Do not create disconnected plan files for each phase unless repository convention requires it.

Freeze each artifact's normative contract projection by revision or content digest; keep phase/task status, phase verdict metadata, blockers, execution checkboxes, diagnostics, and actual revision mappings as explicitly mutable operational state. A Git commit is not required. Apply the profile's independent-review gates. Reviewers may inspect relevant source, manifests, ADRs, dependencies, and evidence, but receive no author conversation or intended answer.

### 4. Execute to Outcome Convergence

For each task:

1. Set it to `implementing`; choose the strongest applicable pre-implementation check and confirm the expected failure or unmet condition when meaningful.
2. Make the smallest coherent implementation.
3. Run targeted automated checks, then the actual applicable effect check. Diagnose and correct the responsible layer until every criterion is current and passing.
4. Record `EVID-*` with requirement/AC/task links, outcome and freshness, an implementation-path content digest (not the not-yet-created commit), candidate mapping when reconciled, time, environment, commands and exit codes, expected/actual result, sanitized artifact paths and hashes, and invalidation conditions.
5. Mark the converged task `completed`, preserving evidence and a coherent owned diff. Continue the remaining tasks in the same phase according to their dependencies.
6. When all phase tasks pass, run the phase's observable checkpoint, reconcile the phase evidence/candidate, set the phase to `awaiting-human-review`, and present a packet containing scope, diff, expected versus actual behavior, evidence, residual risks, and reproducible review steps. Pause before every later phase.
7. On explicit human approval, record reviewer, time, exact phase revision, evidence IDs, and note; then set the phase to `approved` and unlock the next phase. On rejection, record feedback, set the phase to `reopened`, reopen affected tasks, and resume convergence. Any covered change after approval invalidates the phase approval.

Later failures or changed covered inputs mark affected evidence `stale` and reopen owning tasks. Full details, recovery, amendment, review, and blocker rules live in [lifecycle-and-gates.md](references/lifecycle-and-gates.md).

### 5–6. Review, Accept, and Deliver

Independently review the milestone diff against the frozen spec, plan, relevant repository context, and evidence. Every blocking/important finding reopens a task and runs the same convergence loop. Then run the repository's complete applicable gates and cross-task effect checks, update acceptance traceability, and reconcile task state with evidence.

If required authority or external state is unavailable, persist `blocked-permission` or `blocked-external` with the exact resume condition and deliver only the verified artifact/status—not a false Done claim. An accepted risk requires explicit user authorization and, when it changes the contract, an amendment.

Deliver directly when the recorded target is achieved. Deploy/release only when already authorized and planned; record final base/candidate/reviewed/accepted revisions plus release/deployed revisions, rollback readiness, an observed operation-ledger result, and post-release smoke evidence whose authorization exactly matches the release authority.

## Resume Protocol

On every resumed session, read repository instructions, `workflow-state.md`, confirmed requirements/decisions, current spec and plan, amendments, acceptance evidence, Git/worktree state, and active external-operation records. Reconcile the current phase gate, stable task IDs, commit trailers/checkpoints, evidence subject revisions, and actual external state before choosing the next safe action. Never enter a later phase merely from the first unchecked box or from conversation memory.

## Validation Gate

Run the validator throughout development and with `--strict` before claiming the recorded delivery target:

```bash
python3 <skill-root>/scripts/validate_traceability.py <initiative-root> --strict
```

Treat structural checks as evidence only for what they cover. They do not replace tests, runtime checks, independent review, security review, or deployment verification.
