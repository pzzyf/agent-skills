# Workflow State: {{INITIATIVE}}

- Run ID: {{RUN_ID}}
- Artifact root: {{ARTIFACT_ROOT}}
- Rigor: {{PROFILE}}
- Rigor rationale: [replace with risk-based rationale]
- Commit policy: {{COMMIT_POLICY}}
- Delivery target: {{DELIVERY_TARGET}}
- Workflow status: draft
- Technical options status: {{TECHNICAL_OPTIONS_STATUS}}
- Current milestone: M1
- Current phase: none
- Current task: none
- Base revision: {{BASE_REVISION}}
- Initial dirty paths: {{DIRTY_PATHS}}
- Owned paths: [replace before implementation]
- Last checkpoint: none
- Next safe action: Complete capability/authority preflight.
- Review mode: unassessed

## Goal and Boundaries

- Goal: [replace]
- Non-goals: [replace]
- Intended delivery meaning: [implemented, release-ready, or deployed definition for this initiative]

## Capability and Authority Preflight

| Capability/action | Available? | Authorized? | Evidence, boundary, or approval needed |
|---|---|---|---|
| Local read/write | unknown | unknown | [replace] |
| Dependency install | unknown | unknown | [replace] |
| Network/external API | unknown | unknown | [replace] |
| Browser/device | unknown | unknown | [replace] |
| Credentials/secrets | unknown | unknown | Never record values. |
| Production data/system | unknown | no | [replace] |
| Deploy/release | unknown | no | [replace] |
| Destructive/non-idempotent action | unknown | no | [replace] |
| Fresh-context reviewer | unknown | unknown | [replace] |

## Version-Control Baseline

- Repository kind: {{REPOSITORY_KIND}}
- Branch: {{BRANCH}}
- Initial staged paths: {{STAGED_PATHS}}
- Initial unstaged paths: {{UNSTAGED_PATHS}}
- Initial untracked paths: {{UNTRACKED_PATHS}}
- Overlap policy: If the index is already staged or an owned file contains user changes, use `user-managed` or an explicitly authorized isolated worktree; never alter the user's index or stage the whole path blindly.

## Active Resources and Cleanup

| Resource | Identifier/port/path | Owner | State | Cleanup/query action |
|---|---|---|---|---|
| none | none | none | none | none |

## External Operation Ledger

| Operation ID / idempotency key | Target and intended effect | Subject revision | Pre-state | Rollback/recovery | State | Recovery query | Result evidence |
|---|---|---|---|---|---|---|---|
| none | none | none | none | none | none | none | none |

## Retry and Diagnostic State

- Current blocker: none
- Same-cause attempts: 0
- Last hypothesis/result: none
- Next differentiated action: [replace]
- Exact resume condition: none

## Status History

| At | From | To | Reason | Artifact/evidence references |
|---|---|---|---|---|
| {{CREATED_AT}} | none | draft | Workflow initialized. | {{BASE_REVISION}} |
