# Lifecycle and Gates

## Contents

- [Authority and artifact precedence](#authority-and-artifact-precedence)
- [State model](#state-model)
- [Preflight](#preflight)
- [Requirements and decisions](#requirements-and-decisions)
- [Pre-spec spikes](#pre-spec-spikes)
- [Specification and planning](#specification-and-planning)
- [Independent reviews](#independent-reviews)
- [Task convergence](#task-convergence)
- [Amendments and invalidation](#amendments-and-invalidation)
- [Blockers, retries, and accepted risk](#blockers-retries-and-accepted-risk)
- [External side effects](#external-side-effects)
- [Milestone acceptance and delivery](#milestone-acceptance-and-delivery)
- [Resume and reconciliation](#resume-and-reconciliation)

## Authority and Artifact Precedence

Obey the runtime instruction hierarchy supplied by the platform; do not invent a universal rule that current chat text automatically overrides repository instructions or vice versa. Within already-confirmed initiative artifacts, use this dependency order:

1. Confirmed requirements (`REQ-*`) and non-goals
2. Confirmed significant decisions (`DEC-*`)
3. Reviewed specification and acceptance criteria (`AC-*`)
4. Reviewed milestone plan and tasks (`TASK-*`)
5. Existing implementation

Do not resolve a contradiction by silently preferring one layer. Stop the affected work, identify the contradiction, and use the amendment protocol. Never let code retroactively redefine a confirmed contract.

## State Model

Use workflow states:

```text
draft → requirements-confirmed → options-confirmed → specified → planned
→ executing ↔ verifying ↔ fixing → reviewing → accepting
→ implemented | release-ready | deployed
```

Use task states:

```text
pending → implementing → verifying → fixing ↺ → completed
             ↘ blocked-permission | blocked-external | cancelled | accepted-risk
completed → reopened when evidence becomes stale or downstream verification fails
```

Use implementation-phase states:

```text
pending → executing → verifying → awaiting-human-review → approved → next phase
                                      └→ rejected → reopened → affected tasks ↺
```

Keep evidence outcome and freshness orthogonal:

- `Outcome: passed | failed | inconclusive | not-run | not-applicable | accepted-risk`
- `Freshness: current | stale`
- `Blocker: none | permission | external`

Use `not-run` plus a blocker only when evidence cannot be collected; include the exact resume condition. Use `not-applicable` only with a concrete reason. Use `accepted-risk` only when the user explicitly authorized the exact unverified or failed condition; include the authorization and amendment when the acceptance contract changes.

Never aggregate failed, inconclusive, not-run, stale, blocked, or accepted-risk evidence into a completed task or approved phase. `awaiting-human-review` means AI verification and the phase checkpoint have converged, but the next phase remains locked. A workflow may stop safely in a blocked/cancelled/accepted-risk state without claiming success.

## Preflight

Before creating implementation changes:

1. Read repository instructions and locate existing requirements, ADRs, specs, plans, tests, CI, release rules, and artifact conventions.
2. Inspect version-control state without modifying it. Record Git presence, branch, base revision, initial staged/unstaged/untracked paths, and task-owned paths.
3. Select the initiative root and rigor profile. Prefer existing conventions; otherwise use `docs/specs/<initiative>/`.
4. Record the intended delivery target: `implemented`, `release-ready`, or `deployed`.
5. Inventory capability and authority separately for local writes, dependencies, network, browser/device, credentials, external APIs, production data, deployment, destructive operations, and communications.
6. Choose the commit policy and review mode allowed by repository/user rules.
7. Record active processes, ports, temporary resources, cleanup ownership, retry counts, current blocker, and next safe action as they change.

Do not ask for permission merely to inspect safe local state. Ask only when a required action needs authority that has not already been granted.

## Requirements and Decisions

Write requirements as verifiable statements with stable IDs. Include goal, users, scenarios, functional and quality requirements, non-goals, risks/unknowns, success measures, and candidate acceptance criteria.

Use this confirmation sequence:

1. Write status `draft` or `awaiting-confirmation`.
2. Present the bounded requirement set and unresolved questions.
3. Receive explicit confirmation, or identify the originating request that already states the complete bounded contract.
4. Run `validate_traceability.py --print-digests`, then record `confirmed`, confirmer, timestamp, and the emitted canonical requirements digest.

Never pre-write `confirmed` in anticipation of approval.

Bind confirmation to the canonical requirements payload defined in `artifact-contract.md`, not the whole mutable document. For significant decisions, draft the minimum DEC payload needed to compare options, confirm that payload before completing dependent specification sections, and record both the per-DEC and significant-options aggregate digests emitted by the validator. Later prose does not invalidate confirmation unless it changes the canonical decision payload or a linked confirmed requirement.

Classify technical choices:

- **Significant:** architecture, persistence/data ownership, authentication/authorization, public interface, core external integration, deployment topology, migration/lock-in, irreversible choice, or core-flow feasibility. Present evidence-backed options and obtain user confirmation.
- **Tactical:** reversible implementation detail inside confirmed boundaries. Decide autonomously and record when it affects maintenance, behavior, or evidence.

When only one significant option is viable, explain why alternatives fail instead of fabricating choices.

When no significant option exists, record `not-applicable` and continue without a second confirmation round.

## Pre-Spec Spikes

Use `spikes/SPIKE-<nnn>-<slug>.md` for an unknown that blocks a significant decision. Run it after requirements confirmation and before the affected decision is confirmed.

Define:

- one question and decision it blocks;
- time/attempt budget;
- safe environment and cleanup;
- method, commands, inputs, and success/failure thresholds;
- result, confidence, limitations, raw artifact paths/hashes, and decision impact.

Do not require red-green TDD for exploratory code. Keep spike code outside production paths or clearly isolated. Delete it by default after capturing evidence. If any behavior is retained, plan and rewrite it through the normal task verification flow.

Use a planned implementation spike only for a tactical unknown inside an already confirmed option. If it changes requirements, a significant decision, behavior, or acceptance, stop and run an amendment before production implementation continues.

## Specification and Planning

Specify technology-neutral contracts before framework-specific structure:

- scope/non-goals and invariant behavior;
- state/data ownership and lifecycle;
- interfaces and compatibility;
- errors, concurrency, recovery, and boundary conditions;
- security, privacy, migration, rollback, observability, and release behavior when applicable;
- milestones as independently verifiable increments;
- `AC-*` mapped to `REQ-*`, each with a strongest applicable verification method.

Apply only the relevant domain adapter. Mark a field `N/A` with a reason rather than forcing Web, TypeScript, persistence, or UI concepts onto unrelated work.

Plan each milestone from its frozen spec revision. Divide it into ordered implementation phases. Each phase must:

- have a stable `PHASE-M<n>-*` ID, goal, owned ACs/tasks, dependencies, and explicit sequence;
- end in an independently observable checkpoint appropriate to its requirement types;
- define reproducible human review steps and the evidence/artifacts to inspect;
- remain strictly serial with later phases; express genuinely parallel work as tasks inside one phase or as separately governed milestones.

Within each phase, give every task:

- stable ID, state, owning acceptance criteria, dependencies, and owned paths;
- create/modify/delete scope and interfaces/contracts;
- verification strategy selected from the task-type matrix;
- actual effect check and evidence method;
- side-effect/idempotency and cleanup rules;
- invalidation triggers and recovery action;
- prescribed commit/checkpoint behavior consistent with policy.

After review, freeze the plan's normative projection defined in `artifact-contract.md`. Continue updating only operational fields such as task state, blockers/resume conditions, execution checkboxes, diagnostics/history, and actual revision mappings. Those updates do not change `Input contract digest`; any change to scope, behavior, interfaces, acceptance, task ownership, dependencies, owned paths, side-effect sequencing, or verification/evidence contract requires an amendment and affected-delta review. Lite uses the same section-scoped rule inside `change.md`.

## Independent Reviews

Review frozen normative inputs, not moving contracts. Record each input revision/digest, the normalized transitive `Input contract digest`, and repository fingerprint. Specification review binds confirmed requirements and the specification; plan review additionally binds that milestone plan; code review additionally binds the milestone candidate. For code review, both repository fingerprints must equal that candidate revision. Operational status may change after review without changing the digest; changing requirements, specification, normative plan fields, or the candidate invalidates the affected review.

Use fresh context with no author conversation. Provide:

- repository instructions and applicable requirements/spec/plan;
- relevant source, manifests, dependency locks, ADRs, migrations, and tests;
- the actual diff/baselines and sanitized verification evidence;
- profile-specific risks and review questions.

Do not artificially limit a reviewer to the delta when impact scanning shows cross-cutting invariants. Isolate reasoning, not relevant evidence.

Classify findings as `blocking`, `important`, or `minor`, with location, violated contract, impact, and suggested correction. The author fixes blocking/important findings; the same reviewer re-verifies closure. Reopen owning tasks for code findings.

Because a spawned reviewer may share a writable filesystem:

1. Start it without inherited turns when possible.
2. State that it must not edit files or run mutating commands.
3. Never run writer and reviewer concurrently.
4. Compare status/diff/fingerprint after review.
5. Reject contaminated review output and restore only through safe, user-preserving actions.
6. Have the author write the review record.

Apply `independent-passed`, `degraded-reviewed`, and `blocked` exactly as defined in the rigor profile. Never label a same-context review independent.

When an amendment invalidates a review, mark the active record `stale`, preserve it under `reviews/history/<gate>-r<n>.md` as `superseded`, link old and replacement records, and create a new draft at the canonical active path. Do not overwrite or silently reinterpret the old result.

## Task Convergence

Select the verification lead by task type:

| Task type | Required first signal | Required outcome evidence |
|---|---|---|
| New deterministic behavior | Failing focused test | Passing test plus caller/runtime effect when one exists |
| Defect | Failing reproduction or characterization | Regression passes and original failure no longer occurs |
| API/integration | Failing contract/integration check | Real request/response, error, retry/idempotency evidence |
| UI/interaction | Failing interaction/e2e check when feasible | Browser/device interaction, accessibility, viewport/visual evidence |
| Configuration/build | Failing build/lint/contract check | Built artifact and runtime/startup check when applicable |
| Migration/data | Fixture/dry-run that exposes unmet invariant | Migration result, compatibility, integrity, rollback/recovery evidence |
| Performance | Reproducible baseline outside threshold | Comparable measurement within threshold |
| Documentation | Broken link/lint/example or explicit content contract | Rendered/read-back result; no artificial unit test |
| Spike | Unanswered explicit question | Reproducible answer and decision impact; no TDD requirement |

Run this loop:

```text
while any owned criterion is failed, unknown, unverified, contradicted, or stale:
    run the strongest safe check
    diagnose code/test/plan/spec/decision/environment/authority cause
    amend the authoritative layer when required
    correct the cause and add regression coverage
    rerun affected automated and actual-effect checks
    refresh sanitized evidence
```

After each task loop converges, record current evidence and mark that task `completed`; this alone does not unlock the next phase. When every task in the current phase is complete, run the phase checkpoint and present a phase review packet with:

- the phase's linked REQ/AC, tasks, and promised observable outcome;
- the exact phase revision and aggregate owned diff;
- automated checks and actual-effect evidence, including expected versus actual results;
- sanitized artifacts, residual risks, and short reproducible human review steps.

Set the phase to `awaiting-human-review` and pause every later phase. Approval must come from a human after seeing this packet and must name the exact phase candidate. Do not infer approval from silence, the initial requirements confirmation, a generic “continue,” an AI/subagent review, or final milestone acceptance. Record `Human review status: approved`, `Human reviewer`, `Human reviewed at`, `Human review revision`, `Human review evidence`, and `Human review note`. On rejection, record feedback, set the phase to `reopened`, reopen affected tasks, and re-enter their loops. If covered source, configuration, dependency, oracle, AC, checkpoint, or evidence changes afterward, invalidate the phase approval and return to `awaiting-human-review` after reconvergence.

Finalize a passing task in this exact order:

1. Finish automated and actual-effect verification.
2. Write evidence and a digest of the covered implementation/configuration paths or candidate tree. Do not try to embed the future commit SHA inside the commit that creates the evidence.
3. Mark the task `completed`; update next safe action and cleanup state.
4. Inspect owned working/staged diff and confirm no user paths are included.
5. Preserve a coherent recoverable working-tree state. If authorized, create one commit/checkpoint containing code, task state, and evidence; add task/evidence trailers when repository convention permits. During reconciliation/acceptance, keep the per-task subject digest and set its `Candidate mapping` to the accepted candidate revision.

If the commit/checkpoint fails after step 5, preserve state and evidence, record the failure, and resume reconciliation. Do not rerun a successful non-idempotent action merely because Git failed.

## Amendments and Invalidation

Use one amendment path for every contract change:

1. Pause affected tasks and create `AMD-*` with trigger and classification.
2. Identify changed requirements, decisions, spec, plan, acceptance, profile, or authority.
3. Perform impact analysis across IDs, files, milestones, reviews, evidence, compatibility, operations, and rollback.
4. Mark affected evidence/reviews/tasks stale or reopened before relying on them; archive and link superseded review versions as defined by the artifact contract.
5. Update the highest authoritative artifact first.
6. Re-obtain user confirmation if the goal, requirements, non-goals, or a significant option changes.
7. Independently review the affected delta at the profile-required level; expand to full review when impact is cross-cutting or uncertain.
8. Update plans and resume only after the amendment gate passes.

Do not use “re-read the old review,” “backfill with code,” or “fix the plan inline” as bypasses.

Invalidate evidence when any covered source, dependency, configuration, schema, test oracle, acceptance rule, environment assumption, or external state changes. Preserve the old record as `stale`; create a new evidence record after re-verification.

## Blockers, Retries, and Accepted Risk

Do not impose an arbitrary retry cap on deterministic correction, but do not repeat the same failed action blindly. Track attempt count, elapsed diagnostic effort, last hypothesis/result, and next differentiated action.

Escalate the diagnostic level when the same cause persists:

1. Recheck reproduction, logs, and assumptions.
2. Inspect architecture, dependency, environment, and authority boundaries.
3. Run a time-boxed spike or seek external state/authority.
4. Persist a blocker when no safe differentiated action remains.

Use:

- `blocked-permission` when missing authorization/credential is the only remaining dependency.
- `blocked-external` for unavailable service, hardware, environment, human decision, or external state.
- `cancelled` only from user cancellation or superseding work.
- `accepted-risk` only with explicit user authorization naming the exact failed/unverified scope, impact, owner, and expiration/revisit condition. Amend the contract if acceptance criteria change.

A blocked or accepted-risk workflow can be safely handed off, but cannot be described as fully completed.

## External Side Effects

Before a deployment, migration, message, payment, deletion, or other non-idempotent action:

1. Verify authority and exact target with read-only checks.
2. Record a write-ahead entry with operation ID/idempotency key, intended target/effect, subject revision, pre-state, rollback/recovery, and status `prepared`.
3. Persist the entry before executing; commit/checkpoint it when policy and timing allow.
4. Execute once, capture the external operation ID/result, and set `observed` or a blocker state.
5. On interruption, query the external system using the operation ID before any retry.

Never infer production authority from local-write authority. Prefer dry runs, canaries, reversible actions, and explicit target resolution.

Before claiming `deployed`, require `Release authority: principal=<approving person/role>; approval=<immutable approval or change-request ID>`, copy it exactly into each passing release/smoke evidence record's `Authorization`, and reconcile the ledger. Require one ledger section with one table; every row must be complete and use a defined state. At least one `observed` row must bind the deployed revision to current passing release evidence, with concrete target/effect, pre-state, recovery procedure, and recovery query. Resolve every `prepared`, `unknown`, or `blocked-*` entry first.

## Milestone Acceptance and Delivery

For each milestone, record:

- `base_revision`: implementation starting point;
- `candidate_revision`: candidate implementation;
- `reviewed_revision`: revision/digest actually reviewed;
- `accepted_revision`: revision/digest that passed milestone acceptance;
- `release_revision`: immutable release candidate when applicable;
- `deployed_revision`: observed production revision when applicable.

Do not ask a plan to predict a future commit SHA; record the pinning method in the plan and actual revisions during acceptance. Use the prior milestone's accepted revision as the next milestone's base.

Before a delivery claim, reconcile workflow base to acceptance base; every milestone's reviewed/accepted revision to its candidate; each later milestone base to the prior accepted revision; the final milestone's candidate/reviewed/accepted values to acceptance; release-plan candidate/release/deployed values to acceptance; and every current passing evidence `Candidate mapping` to the accepted candidate. Preserve each per-task covered-path `Subject revision`; a deployed smoke/observation record must additionally name the observed deployed revision as its subject.

Run repository-defined tests, lint, type checks, builds, security/data checks, and the applicable cross-task actual-effect suite. Map every `AC-*` to current `EVID-*`. Reopen owning tasks for any failure or stale/unknown evidence, then repeat code review and affected/full regression as required.

Use delivery labels precisely:

- `implemented`: code and local evidence are complete; release work may remain.
- `release-ready`: all pre-release gates, packaging, migration/rollback preparation, and required reviews pass.
- `deployed`: the exact authorized revision is represented by an `observed` operation-ledger row, its authority matches current release evidence, no external operation is unresolved, and post-deploy smoke/observability checks pass.

Record residual minor findings and accepted risks without hiding them. Deliver the completed artifact directly when the target is achieved; identify only genuinely external or unauthorized remaining actions.

## Resume and Reconciliation

On resume:

1. Read repository instructions and all authoritative initiative artifacts.
2. Inspect current Git/non-Git revision, dirty/index state, and task-owned paths.
3. Reconcile workflow/phase/task statuses against human phase verdicts, commits/checkpoints, task/evidence trailers, subject digests, acceptance mappings, and review baselines.
4. Query any prepared/unknown external operation before acting.
5. Reconcile active processes, ports, temporary resources, and cleanup state.
6. Mark contradicted evidence stale and reopen affected tasks.
7. Continue from `next safe action`, updating it if current evidence disproves it.

Never assume an unchecked task is unexecuted or a checked task is valid. Persisted status is a claim to reconcile, not unquestionable truth.
