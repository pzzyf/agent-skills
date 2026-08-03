# Milestone Plan: {{INITIATIVE}} / {{MILESTONE}}

- Plan status: draft
- Spec revision: pending
- Base revision: {{BASE_REVISION}}
- Candidate revision: pending
- Reviewed revision: pending
- Accepted revision: pending
- Release revision: not-applicable
- Deployed revision: not-applicable
- Pinning method: [record method now; actual revision during acceptance]

## Goal and Spec Mapping

[State the independently verifiable increment and mapped spec/AC IDs.]

## Constraints and Non-Goals

[Repository rules, confirmed choices, safety boundaries, and explicit non-scope.]

## Phased Implementation Strategy

[Keep one milestone plan. Divide it into ordered phases/chunks; each phase contains multiple typed tasks/steps and ends with an observable checkpoint plus a human review gate. Later phases stay locked until approval.]

### PHASE-{{MILESTONE}}-001 — [Phase title]

- Status: pending
- Sequence: 1
- Depends on: none
- Goal: [independently observable phase outcome]
- Acceptance: AC-001
- Tasks: TASK-{{MILESTONE}}-001
- Verification checkpoint: [aggregate commands/interactions, visible expected result, and common failure signals]
- Checkpoint revision: pending
- Human review procedure: [short reproducible steps and exact artifacts the human must inspect]
- Human review status: pending
- Human reviewer: none
- Human reviewed at: none
- Human review revision: pending
- Human review evidence: pending
- Human review note: pending

### TASK-{{MILESTONE}}-001 — [Task title]

- Status: pending
- Phase: PHASE-{{MILESTONE}}-001
- Acceptance: AC-001
- Verification class: pending
- Dependencies: none
- Owned paths: [explicit create/modify/delete paths]
- Interfaces/contracts: [replace or N/A with reason]
- First signal: [failing test/reproduction/contract/unmet condition or justified N/A]
- Targeted checks: [commands/procedures]
- Outcome check: [runtime/API/browser/device/data/performance/observation result]
- Evidence method: [EVID record inputs and artifact]
- Side effects/idempotency: none or [intent/key/query/recovery]
- Cleanup: [processes, ports, temp data, devices]
- Invalidation: [inputs that reopen this task]
- Blocker: none
- Resume condition: none
- Commit/checkpoint: follow workflow-state policy; code + state + evidence remain reconcilable

#### Steps

- [ ] Establish first signal or record a justified non-test baseline.
- [ ] Implement the smallest coherent change.
- [ ] Run targeted automated checks.
- [ ] Run actual-effect checks.
- [ ] Correct failures and rerun affected checks.
- [ ] Record current evidence.
- [ ] Mark the verified task `completed` and inspect owned diff.
- [ ] Create an authorized commit/checkpoint, or leave coherent user-managed state.

### Phase Checkpoint and Human Gate

- [ ] Complete every task owned by this phase and reconcile its evidence.
- [ ] Run the phase verification checkpoint and capture the observable result.
- [ ] Set the phase to `awaiting-human-review` and present the aggregate review packet.
- [ ] Pause every later phase until explicit human approval.
- [ ] Record approval and set `approved`, or record rejection, set `reopened`, and reopen affected tasks.

## Milestone Definition of Done

[Map every owned AC to phases/tasks, current evidence method, every phase gate, and full regression/effect check.]
