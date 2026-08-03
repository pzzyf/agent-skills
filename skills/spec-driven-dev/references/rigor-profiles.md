# Rigor Profiles

## Contents

- [Selection rules](#selection-rules)
- [Lite](#lite)
- [Standard](#standard)
- [High-assurance](#high-assurance)
- [Escalation and de-escalation](#escalation-and-de-escalation)
- [Review modes](#review-modes)
- [Commit policies](#commit-policies)

## Selection Rules

Choose rigor from risk, not line count. Record the selected profile and rationale in `workflow-state.md` before implementation.

Use the highest applicable signal:

| Signal | Minimum profile |
|---|---|
| Reversible change, one bounded area, no significant technical choice | Lite |
| Cross-module feature, new public behavior, core external integration, meaningful operational work, reversible non-production migration | Standard |
| Authentication/authorization, security/privacy, money, destructive or irreversible data change, sensitive/regulated or production migration, production infrastructure, safety-critical behavior, difficult rollback | High-assurance |

Treat a tiny authentication edit or a production/sensitive/destructive migration as high risk even if it changes one line. Use Lite for a behavior-preserving refactor only when it stays inside one provable impact domain; use Standard for a large or cross-module mechanical refactor and for reversible non-production migrations even when rollback is easy.

Honor an explicitly requested stricter profile. Do not silently choose a weaker profile than the risk signals or repository policy require.

## Lite

Use Lite only when all of these are true:

- The change is local, reversible, and low blast radius.
- No significant technical option needs confirmation.
- No credential, production, migration, privacy, security, or destructive-data risk exists.
- One milestone and a compact acceptance surface are sufficient.

Use these artifacts:

- `workflow-state.md`
- `change.md`, combining `REQ-*`, any tactical `DEC-*`, `AC-*`, and `TASK-M1-*`
- `reviews/code-review-M1.md`
- `reviews/acceptance.md`
- amendments or spikes only if they become necessary

Keep both user requirements confirmation and evidence-backed completion. Use one pre-implementation consistency pass and one code review. A fresh-context independent code review is preferred; `degraded-reviewed` may proceed only when repository policy does not require independence, the risk remains Lite, and the review record names the limitation.

Escalate to Standard before continuing if a significant option, cross-module impact, new external dependency, ambiguous rollback, or broader acceptance surface appears.

## Standard

Use Standard for ordinary product features and cross-module work.

Use these artifacts:

- `workflow-state.md`
- `requirements.md`
- `spikes/SPIKE-*` as needed before decision confirmation
- `spec.md`
- `plans/M<n>-*.md`
- `amendments/AMD-*` as needed
- independent spec, plan, and code review records
- `reviews/acceptance.md`

Require fresh-context independent spec, plan, and code reviews when available. If independence is unavailable, allow `degraded-reviewed` only when:

1. Repository/user policy does not require an independent reviewer.
2. No High-assurance signal exists.
3. The author records why isolation was unavailable, the repository fingerprint before and after review, the expanded self-review checks, and residual risk.
4. The user is asked only when proceeding would materially change the agreed assurance level or external risk.

Otherwise set `blocked-permission` or `blocked-external` and record the resume condition.

## High-Assurance

Use High-assurance for any material security, privacy, authentication, money, destructive data, sensitive/regulated or production migration, production-infrastructure, safety, or hard-to-reverse risk.

Use every Standard artifact plus `release-plan.md`, and require:

- explicit threat/privacy/data-flow analysis as applicable;
- compatibility and migration invariants, backups, dry runs, rollback, and recovery rehearsal;
- dependency/supply-chain and secret-handling checks;
- test-data isolation and production-access boundaries;
- observability and recovery criteria, plus rollout, alert, rollback, and post-release smoke criteria when the delivery target includes release/deployment;
- independent reviews without degraded substitution;
- exact base, candidate, reviewed, and accepted revisions, plus release/deployed revisions only when applicable to the target;
- explicit authority before production mutation;
- at least one recovery or rollback evidence item when rollback is applicable.

Judge High-assurance completion against the recorded delivery target. Required independent review and target-applicable evidence must be available in every case. Require release authority and post-release evidence only for a `deployed` target; require release/rollback readiness but not production authority for `release-ready`. Use a blocked state when evidence required for the chosen target is unavailable.

## Escalation and De-Escalation

Escalate immediately when evidence reveals a higher-risk signal. Record an `AMD-*` entry if the artifact contract, gates, or acceptance scope changes, invalidate affected reviews/evidence, create missing profile artifacts, and re-review the affected delta.

Do not de-escalate merely to avoid a blocked gate. De-escalate only when evidence proves the original risk classification was wrong, repository/user policy permits it, and an amendment records the rationale and affected assurance claims. Never de-escalate High-assurance work after a production or irreversible action has begun.

## Review Modes

Use exactly one review status:

- `independent-passed`: a fresh isolated context reviewed the frozen inputs; all blocking and important findings are closed.
- `degraded-reviewed`: independence was unavailable; the allowed profile conditions above are satisfied and limitations are recorded.
- `blocked`: the required review cannot run or has open blocking/important findings.
- `draft`: the active review has not completed.
- `stale`: the active review's normative input digest was invalidated and a replacement is required.
- `superseded`: an archived review was replaced by a named later review.

Treat prompts that say “read-only” as intent, not enforcement. For an independent review:

1. Freeze input revisions or content digests.
2. Start the reviewer with no inherited turns when the platform supports it (for example `fork_turns: "none"`).
3. Provide raw artifacts and relevant repository context, not author reasoning, expected findings, or hidden ground truth.
4. Do not run a writer concurrently.
5. Compare repository status/diff/fingerprint after the review; discard and rerun a review that mutated inputs.
6. Have the author, not the reviewer, record the review result in the worktree.

## Commit Policies

Choose one policy from explicit user/repository authorization:

- `auto`: commit each reviewed artifact or completed task boundary. Stage only owned paths, inspect the staged diff, and include code, state, and evidence in the same task commit.
- `checkpoint`: keep task state/evidence synchronized, then commit at reviewed artifact or milestone checkpoints rather than every task. Use content digests between commits.
- `user-managed`: never stage or commit. Maintain coherent working-tree state and content digests so the user can commit later.

Default to `user-managed` when authorization is absent. In every mode:

- Record Git/non-Git status, branch, base revision, initial dirty paths, and task-owned paths.
- Preserve unrelated user changes and pre-existing index entries.
- If the index already contains staged content, switch to `user-managed` or an explicitly authorized isolated worktree; never commit, unstage, or absorb the user's index as a side effect.
- If an initially dirty file overlaps a task-owned file, do not stage the whole path. Switch to `user-managed`, isolate the work in an explicitly authorized worktree, or obtain a precise user-approved integration method.
- Never use `git add -A`, broad globs, amend, reset, rebase, force push, or cleanup as a workflow shortcut.
- Treat hook, GPG, identity, or permission failures as commit failures, not implementation failures. Preserve the completed state/evidence and record the next safe action.
- Use a content digest or explicit revision when Git is absent. A commit is never the only proof that a gate passed.
