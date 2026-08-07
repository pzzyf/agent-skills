---
name: push-reviewed-diff
description: "Push the current branch's reviewed changes directly to origin after the user explicitly approves them. Use when the user has reviewed the current diff and asks to push/推送 to origin (e.g. 审核通过、没问题、直接推送), or when Codex must verify the diff to be pushed exactly matches what was reviewed, commit the reviewed changes if needed, push without force, and confirm the remote state. Do not use for opening pull requests, force-pushing, deploying, or pushing without explicit user approval."
---

# Push Reviewed Diff

## Trigger and Approval

- Trigger only when the user explicitly approves the current diff **and** asks to push it to origin. Examples: "审核完了，直接推到 origin" / "diff 没问题，推送吧".
- "Reviewed" alone is not a push instruction; "push" alone is not approval of the current diff. Require both.
- Do not create a PR, tag, deploy, or force-push as part of this workflow.

## Workflow

1. Capture the baseline:
   - `git status --porcelain=v1 -b`
   - `git diff --stat HEAD`
   - `git branch --show-current`
   - Upstream: `git rev-parse --abbrev-ref --symbolic-full-name @{u}` (may fail; that's fine for new branches)
   - Local commits ahead: `git log --oneline @{u}..HEAD`, or `git log --oneline origin/<branch>..HEAD` when no upstream exists.
   - Read repository instructions and respect any commit or push policy.

2. Verify the scope matches what was reviewed:
   - The changes to push = uncommitted diff + local commits ahead of upstream (or all commits on a new branch).
   - If anything changes after this baseline (new edits, staged changes, untracked files), stop and confirm before pushing.
   - Check for dangerous content: credentials/secrets, generated artifacts that should not ship, broad deletions, unexpected submodule or large-file changes. Stop and report anything suspicious.

3. Commit only if needed:
   - No changes at all → stop and report that there is nothing to push; never create an empty commit.
   - Clean tree with commits ahead → skip to push.
   - Uncommitted changes:
     - If repository instructions prohibit agent commits, stop and ask the user to commit.
     - Stage only paths that are part of the reviewed diff. Never use `git add -A` or `git add .` blindly; if unrelated pre-existing staged/dirty files exist, stop and confirm.
     - Inspect `git diff --cached --stat` and `git diff --cached` before committing.
     - Create one commit with a concise conventional message derived from the diff. If the changes are unrelated or the message is ambiguous, stop and ask.

4. Push:
   - With an upstream: `git push origin <branch>`
   - New branch / no upstream: `git push -u origin <branch>`
   - Never use `--force` or `--force-with-lease` unless the user explicitly asked. If the remote rejects as non-fast-forward, stop and report the divergence; do not rewrite history or overwrite remote state.

5. Verify and report:
   - `git ls-remote origin <branch>` and compare remote HEAD with `git rev-parse HEAD`.
   - `git status -sb` should show the branch in sync.
   - Report: pushed commit(s), branch, remote URL, and confirmation that remote HEAD equals local HEAD. If verification fails, report the exact state; do not claim success.

## Notes

- Push to `origin` only; do not substitute another remote.
- If `origin` is missing or branch protection rejects the push, report the error and stop.
- If the user later wants to change an already-pushed commit, require explicit force-push approval.
