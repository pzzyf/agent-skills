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

## Task-Type Verification Strategy

[Select applicable verification leads; do not force a meaningless unit test.]

### TASK-{{MILESTONE}}-001 — [Task title]

- Status: pending
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
- [ ] Mark task state and inspect owned diff.
- [ ] Create an authorized commit/checkpoint, or leave coherent user-managed state.

## Milestone Definition of Done

[Map every owned AC to a task, current evidence method, review gate, and full regression/effect check.]
