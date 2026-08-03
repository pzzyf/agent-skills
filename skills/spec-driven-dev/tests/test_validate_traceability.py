from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "validate_traceability.py"
BASE = "a" * 64
CANDIDATE = "b" * 64


class ValidateTraceabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "initiative"
        (self.root / "reviews").mkdir(parents=True)
        self.write_valid_lite()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_validator(self, *args: str, root: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(root or self.root), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    @staticmethod
    def set_first_field(path: Path, field: str, value: str) -> None:
        lines = path.read_text(encoding="utf-8").splitlines()
        prefix = f"- {field}:"
        for index, line in enumerate(lines):
            if line.startswith(prefix):
                lines[index] = f"{prefix} {value}"
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return

    @staticmethod
    def set_definition_field(path: Path, identifier: str, field: str, value: str) -> None:
        lines = path.read_text(encoding="utf-8").splitlines()
        inside = False
        prefix = f"- {field}:"
        for index, line in enumerate(lines):
            if re.match(rf"^#{{2,6}}\s+{re.escape(identifier)}\s+(?:—|-)\s+", line):
                inside = True
                continue
            if inside and re.match(r"^#{1,6}\s+", line):
                break
            if inside and line.startswith(prefix):
                lines[index] = f"{prefix} {value}"
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return

    def refresh_digests(self) -> None:
        result = self.run_validator("--print-digests")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = json.loads(result.stdout)
        contract = self.root / ("change.md" if (self.root / "change.md").exists() else "requirements.md")
        self.set_first_field(contract, "Confirmed revision", manifest["requirements"])
        spec = self.root / "spec.md"
        if spec.exists():
            self.set_first_field(spec, "Requirements revision", manifest["requirements"])
            if manifest.get("technical_options"):
                self.set_first_field(spec, "Options confirmed revision", manifest["technical_options"])
        for identifier, digest in manifest["decisions"].items():
            for path in self.root.rglob("*.md"):
                if re.search(rf"(?m)^#{{2,6}}\s+{re.escape(identifier)}\s+(?:—|-)\s+", path.read_text(encoding="utf-8")):
                    self.set_definition_field(path, identifier, "Confirmed revision", digest)
                    break
        if manifest.get("specification"):
            for plan in (self.root / "plans").glob("*.md"):
                self.set_first_field(plan, "Spec revision", manifest["specification"])
        for relative, digest in manifest["reviews"].items():
            self.set_first_field(self.root / relative, "Input contract digest", digest)

    def convert_to_standard_m1(self) -> None:
        state = self.root / "workflow-state.md"
        state.write_text(
            state.read_text(encoding="utf-8")
            .replace("Rigor: lite", "Rigor: standard")
            .replace("Rigor rationale: Low-risk reversible single-domain change.", "Rigor rationale: Cross-module standard fixture."),
            encoding="utf-8",
        )
        (self.root / "change.md").unlink()
        (self.root / "requirements.md").write_text(
            f"""# Requirements: sample
- Requirements status: confirmed
- Confirmed by: originating user request
- Confirmed at: 2026-08-03T11:00:00Z
- Confirmed revision: sha256:{BASE}

## Product Goal
Return the stable documented value.

## Non-Goals
No unrelated interface changes.

## REQ-001 — Return a stable value
- Statement: The public function returns the documented value.
""",
            encoding="utf-8",
        )
        (self.root / "spec.md").write_text(
            f"""# Specification: sample
- Spec status: reviewed
- Requirements revision: sha256:{BASE}
- Technical options status: not-applicable
- Options confirmed by: none
- Options confirmed at: none
- Options confirmed revision: none

## Behavior
The existing public function returns its stable value.

## AC-001 — Stable value is observed
- Requirements: REQ-001
- Verification class: unit
- Method: Focused unit test.
- Passing condition: The assertion passes.
""",
            encoding="utf-8",
        )
        plans = self.root / "plans"
        plans.mkdir()
        (plans / "M1-plan.md").write_text(
            f"""# Milestone Plan M1
- Plan status: accepted
- Spec revision: sha256:{BASE}
- Base revision: sha256:{BASE}
- Candidate revision: sha256:{CANDIDATE}
- Reviewed revision: sha256:{CANDIDATE}
- Accepted revision: sha256:{CANDIDATE}
- Release revision: not-applicable
- Deployed revision: not-applicable

## TASK-M1-001 — Implement the stable value
- Status: completed
- Acceptance: AC-001
- Verification class: unit
- Dependencies: none
- Owned paths: src/example.py
- Blocker: none
- Resume condition: none
""",
            encoding="utf-8",
        )
        review_path = self.root / "reviews" / "code-review-M1.md"
        review_path.write_text(review_path.read_text(encoding="utf-8").replace("Rigor: lite", "Rigor: standard"), encoding="utf-8")
        review = review_path.read_text(encoding="utf-8")
        (self.root / "reviews" / "spec-review.md").write_text(review, encoding="utf-8")
        (self.root / "reviews" / "plan-review-M1.md").write_text(review, encoding="utf-8")
        self.refresh_digests()

    def extend_standard_to_m2(self) -> None:
        self.convert_to_standard_m1()
        middle = "c" * 64
        state = self.root / "workflow-state.md"
        state.write_text(state.read_text(encoding="utf-8").replace("Current milestone: M1", "Current milestone: M2"), encoding="utf-8")
        plan1 = self.root / "plans" / "M1-plan.md"
        plan1.write_text(
            plan1.read_text(encoding="utf-8")
            .replace(f"Candidate revision: sha256:{CANDIDATE}", f"Candidate revision: sha256:{middle}")
            .replace(f"Reviewed revision: sha256:{CANDIDATE}", f"Reviewed revision: sha256:{middle}")
            .replace(f"Accepted revision: sha256:{CANDIDATE}", f"Accepted revision: sha256:{middle}"),
            encoding="utf-8",
        )
        (self.root / "plans" / "M2-plan.md").write_text(
            f"""# Milestone Plan M2
- Plan status: accepted
- Spec revision: sha256:{BASE}
- Base revision: sha256:{middle}
- Candidate revision: sha256:{CANDIDATE}
- Reviewed revision: sha256:{CANDIDATE}
- Accepted revision: sha256:{CANDIDATE}
- Release revision: not-applicable
- Deployed revision: not-applicable

## TASK-M2-001 — Reconcile the final candidate
- Status: completed
- Acceptance: AC-001
- Verification class: unit
- Dependencies: TASK-M1-001
- Owned paths: src/example.py
- Blocker: none
- Resume condition: none
""",
            encoding="utf-8",
        )
        acceptance = self.root / "reviews" / "acceptance.md"
        with acceptance.open("a", encoding="utf-8") as handle:
            handle.write("\n" + self.evidence_block("EVID-002").replace("TASK-M1-001", "TASK-M2-001"))
        review_path = self.root / "reviews" / "code-review-M1.md"
        review_path.write_text(review_path.read_text(encoding="utf-8").replace("Rigor: lite", "Rigor: standard"), encoding="utf-8")
        self.set_first_field(review_path, "Repository fingerprint before", f"sha256:{middle}")
        self.set_first_field(review_path, "Repository fingerprint after", f"sha256:{middle}")
        review = review_path.read_text(encoding="utf-8")
        (self.root / "reviews" / "plan-review-M2.md").write_text(review, encoding="utf-8")
        (self.root / "reviews" / "code-review-M2.md").write_text(review, encoding="utf-8")
        self.set_first_field(self.root / "reviews" / "code-review-M2.md", "Repository fingerprint before", f"sha256:{CANDIDATE}")
        self.set_first_field(self.root / "reviews" / "code-review-M2.md", "Repository fingerprint after", f"sha256:{CANDIDATE}")
        self.refresh_digests()

    def write_valid_lite(self) -> None:
        (self.root / "workflow-state.md").write_text(
            f"""# Workflow State: sample

- Run ID: SDD-20260803-sample
- Artifact root: docs/specs/sample
- Rigor: lite
- Rigor rationale: Low-risk reversible single-domain change.
- Commit policy: user-managed
- Delivery target: implemented
- Workflow status: implemented
- Technical options status: not-applicable
- Current milestone: M1
- Current task: none
- Base revision: sha256:{BASE}
- Initial dirty paths: none
- Initial staged paths: none
- Owned paths: src/example.py
- Last checkpoint: 2026-08-03T12:00:00Z
- Next safe action: Deliver verified implementation.
- Review mode: independent
- Current blocker: none
- Exact resume condition: none
""",
            encoding="utf-8",
        )
        (self.root / "change.md").write_text(
            f"""# Lite Change Contract: sample

- Requirements status: confirmed
- Confirmed by: originating user request
- Confirmed at: 2026-08-03T11:00:00Z
- Confirmed revision: sha256:{BASE}
- Technical options status: not-applicable
- Base revision: sha256:{BASE}
- Candidate revision: sha256:{CANDIDATE}
- Reviewed revision: sha256:{CANDIDATE}
- Accepted revision: sha256:{CANDIDATE}
- Release revision: not-applicable
- Deployed revision: not-applicable

## Goal and Non-Goals

Return the stable documented value; do not change unrelated interfaces.

## REQ-001 — Return a stable value

- Statement: The public function returns the documented value.

## AC-001 — Stable value is observed

- Requirements: REQ-001
- Verification class: unit
- Method: Focused unit test.
- Passing condition: The assertion passes.

## Milestone M1

### TASK-M1-001 — Implement the stable value

- Status: completed
- Acceptance: AC-001
- Verification class: unit
- Dependencies: none
- Owned paths: src/example.py
- Blocker: none
- Resume condition: none
""",
            encoding="utf-8",
        )
        (self.root / "reviews" / "code-review-M1.md").write_text(
            """# Code Review M1: sample

- Status: independent-passed
- Rigor: lite
- Reviewer/context: fresh-context-reviewer
- Isolation method: empty inherited history; read-only prompt
- Reviewed at: 2026-08-03T12:10:00Z
- Input contract digest: sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
- Repository fingerprint before: sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
- Repository fingerprint after: sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
- Open blocking findings: 0
- Open important findings: 0
""",
            encoding="utf-8",
        )
        self.write_acceptance()
        self.refresh_digests()

    def evidence_block(
        self,
        identifier: str = "EVID-001",
        outcome: str = "passed",
        freshness: str = "current",
        verification_class: str = "unit",
        artifacts: str = "none",
        authorization: str = "not-applicable",
    ) -> str:
        return f"""### {identifier} — Focused verification

- Acceptance: AC-001
- Task: TASK-M1-001
- Outcome: {outcome}
- Freshness: {freshness}
- Blocker: none
- Verification class: {verification_class}
- Subject revision: sha256:{CANDIDATE}
- Candidate mapping: sha256:{CANDIDATE}
- Recorded at: 2026-08-03T12:05:00Z
- Environment: Python 3.13 on local fixture
- Method: `python -m unittest test_example.py`
- Exit code: 0
- Expected: The documented stable value is returned.
- Actual: One focused assertion passed.
- Artifacts: {artifacts}
- Sanitization: No credentials or personal data recorded.
- Cleanup: No active process or temporary resource.
- Invalidation: stale when source, test, runtime, or AC-001 changes.
- Authorization: {authorization}
- Risk scope: not-applicable
- Risk impact: not-applicable
- Risk owner: not-applicable
- Risk expiry/revisit: not-applicable
"""

    def append_deployment_ledger(
        self,
        operation_id: str = "RELEASE-1",
        revision: str = CANDIDATE,
        evidence: str = "EVID-002",
        state: str = "observed",
    ) -> None:
        with (self.root / "workflow-state.md").open("a", encoding="utf-8") as handle:
            handle.write(
                f"""

## External Operation Ledger

| Operation ID / idempotency key | Target and intended effect | Subject revision | Pre-state | Rollback/recovery | State | Recovery query | Result evidence |
|---|---|---|---|---|---|---|---|
| {operation_id} | production deployment of sample | sha256:{revision} | prior revision recorded | redeploy prior revision | {state} | query production version endpoint | {evidence} |
"""
            )

    def configure_complete_deployment(
        self,
        *,
        release_authority: str = "principal=user; approval=RELEASE-1",
        evidence_authorization: str | None = None,
        ledger_state: str = "observed",
    ) -> None:
        state = self.root / "workflow-state.md"
        state.write_text(
            state.read_text(encoding="utf-8")
            .replace("Delivery target: implemented", "Delivery target: deployed")
            .replace("Workflow status: implemented", "Workflow status: deployed"),
            encoding="utf-8",
        )
        for path in (self.root / "change.md", self.root / "reviews" / "acceptance.md"):
            content = path.read_text(encoding="utf-8")
            if path.name == "acceptance.md":
                content = content.replace("Delivery target: implemented", "Delivery target: deployed")
                content += "\n" + self.evidence_block(
                    "EVID-002",
                    verification_class="release",
                    authorization=evidence_authorization or release_authority,
                )
            content = content.replace("Release revision: not-applicable", f"Release revision: sha256:{CANDIDATE}")
            content = content.replace("Deployed revision: not-applicable", f"Deployed revision: sha256:{CANDIDATE}")
            path.write_text(content, encoding="utf-8")
        (self.root / "release-plan.md").write_text(
            f"""# Release Plan
- Status: deployed
- Delivery target: deployed
- Candidate revision: sha256:{CANDIDATE}
- Release revision: sha256:{CANDIDATE}
- Deployed revision: sha256:{CANDIDATE}
- Release authority: {release_authority}
""",
            encoding="utf-8",
        )
        self.append_deployment_ledger(state=ledger_state)

    def write_acceptance(self, evidence: str | None = None) -> None:
        (self.root / "reviews" / "acceptance.md").write_text(
            f"""# Acceptance and Evidence: sample

- Acceptance status: accepted
- Delivery target: implemented
- Base revision: sha256:{BASE}
- Candidate revision: sha256:{CANDIDATE}
- Reviewed revision: sha256:{CANDIDATE}
- Accepted revision: sha256:{CANDIDATE}
- Release revision: not-applicable
- Deployed revision: not-applicable

## Evidence Records

{evidence or self.evidence_block()}
""",
            encoding="utf-8",
        )

    def test_valid_lite_passes_strict(self) -> None:
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_valid_standard_passes_strict(self) -> None:
        self.convert_to_standard_m1()
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_valid_high_assurance_implemented_target_passes_strict(self) -> None:
        self.convert_to_standard_m1()
        state = self.root / "workflow-state.md"
        state.write_text(state.read_text(encoding="utf-8").replace("Rigor: standard", "Rigor: high-assurance"), encoding="utf-8")
        for review in (self.root / "reviews").glob("*.md"):
            review.write_text(review.read_text(encoding="utf-8").replace("Rigor: standard", "Rigor: high-assurance"), encoding="utf-8")
        (self.root / "release-plan.md").write_text(
            f"""# Release Plan: sample
- Status: not-applicable
- Delivery target: implemented
- Candidate revision: sha256:{CANDIDATE}
- Release revision: not-applicable
- Deployed revision: not-applicable
- Release authority: not-applicable

## Scope
Release and deployment are outside this implemented target.
""",
            encoding="utf-8",
        )
        self.refresh_digests()
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unversioned_and_unborn_bases_can_reconcile_strictly(self) -> None:
        paths = [self.root / "workflow-state.md", self.root / "change.md", self.root / "reviews" / "acceptance.md"]
        originals = {path: path.read_text(encoding="utf-8") for path in paths}
        for sentinel in ("unversioned", "git:unborn"):
            with self.subTest(sentinel=sentinel):
                for path, content in originals.items():
                    path.write_text(content.replace(f"Base revision: sha256:{BASE}", f"Base revision: {sentinel}"), encoding="utf-8")
                result = self.run_validator("--strict")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fenced_example_ids_are_ignored(self) -> None:
        with (self.root / "change.md").open("a", encoding="utf-8") as handle:
            handle.write("\n```markdown\n## REQ-001 — Example only\n```\n")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_indented_fences_and_html_comments_are_inactive(self) -> None:
        with (self.root / "change.md").open("a", encoding="utf-8") as handle:
            handle.write(
                """
   ```markdown
   ## REQ-001 — Inactive fenced duplicate
   ```

<!--
## REQ-001 — Inactive commented duplicate
-->
"""
            )
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_inactive_placeholders_do_not_block_strict_delivery(self) -> None:
        with (self.root / "change.md").open("a", encoding="utf-8") as handle:
            handle.write(
                """
```markdown
- Status: pending
{{INACTIVE_TOKEN}}
[replace this inactive example]
```

<!--
- Status: unknown
{{INACTIVE_COMMENT_TOKEN}}
-->
"""
            )
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_backtick_in_fence_info_does_not_hide_active_contract(self) -> None:
        with (self.root / "change.md").open("a", encoding="utf-8") as handle:
            handle.write(
                """
```markdown`not-a-commonmark-fence
## DEC-001 — Must remain active
- Significant option: yes
- Status: recorded
- Confirmed by: none
- Confirmed at: none
- Confirmed revision: none
"""
            )
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("decision-unconfirmed", result.stdout)

    def test_requirement_payload_edit_invalidates_confirmation(self) -> None:
        change = self.root / "change.md"
        change.write_text(change.read_text(encoding="utf-8").replace("returns the documented value", "returns a different value"), encoding="utf-8")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("requirements-digest-mismatch", result.stdout)

    def test_normative_plan_edit_invalidates_review_digest(self) -> None:
        change = self.root / "change.md"
        change.write_text(change.read_text(encoding="utf-8").replace("Owned paths: src/example.py", "Owned paths: src/other.py"), encoding="utf-8")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("review-contract-digest-mismatch", result.stdout)

    def test_upstream_requirement_edit_invalidates_all_standard_reviews(self) -> None:
        self.convert_to_standard_m1()
        requirements = self.root / "requirements.md"
        requirements.write_text(
            requirements.read_text(encoding="utf-8").replace(
                "returns the documented value",
                "returns the newly documented value",
            ),
            encoding="utf-8",
        )
        manifest = json.loads(self.run_validator("--print-digests").stdout)
        self.set_first_field(requirements, "Confirmed revision", manifest["requirements"])
        self.set_first_field(self.root / "spec.md", "Requirements revision", manifest["requirements"])
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertGreaterEqual(result.stdout.count("review-contract-digest-mismatch"), 3)

    def test_candidate_edit_invalidates_code_review(self) -> None:
        replacement = "d" * 64
        for path in (self.root / "change.md", self.root / "reviews" / "acceptance.md"):
            content = path.read_text(encoding="utf-8")
            content = content.replace(f"Candidate revision: sha256:{CANDIDATE}", f"Candidate revision: sha256:{replacement}")
            content = content.replace(f"Reviewed revision: sha256:{CANDIDATE}", f"Reviewed revision: sha256:{replacement}")
            content = content.replace(f"Accepted revision: sha256:{CANDIDATE}", f"Accepted revision: sha256:{replacement}")
            content = content.replace(f"Candidate mapping: sha256:{CANDIDATE}", f"Candidate mapping: sha256:{replacement}")
            path.write_text(content, encoding="utf-8")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("review-contract-digest-mismatch", result.stdout)
        self.assertIn("review-candidate-mismatch", result.stdout)

    def test_operational_checkbox_does_not_invalidate_review_digest(self) -> None:
        with (self.root / "change.md").open("a", encoding="utf-8") as handle:
            handle.write("\n- [x] Runtime bookkeeping completed.\n")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_confirmed_decision_payload_edit_invalidates_confirmation(self) -> None:
        self.convert_to_standard_m1()
        state = self.root / "workflow-state.md"
        state.write_text(state.read_text(encoding="utf-8").replace("Technical options status: not-applicable", "Technical options status: confirmed"), encoding="utf-8")
        spec = self.root / "spec.md"
        content = spec.read_text(encoding="utf-8")
        content = content.replace("Technical options status: not-applicable", "Technical options status: confirmed")
        content = content.replace("Options confirmed by: none", "Options confirmed by: originating user request")
        content = content.replace("Options confirmed at: none", "Options confirmed at: 2026-08-03T11:30:00Z")
        content += f"""

## DEC-001 — Select the stable implementation
- Significant option: yes
- Status: confirmed
- Requirements/risks: REQ-001
- Chosen option: option-a
- Evidence/spikes: repository inspection
- Benefits and costs: bounded change with no new dependency
- Operational/migration/lock-in consequences: none
- Rejected alternatives and reasons: option-b adds unnecessary coupling
- Confirmed by: originating user request
- Confirmed at: 2026-08-03T11:30:00Z
- Confirmed revision: sha256:{BASE}
"""
        spec.write_text(content, encoding="utf-8")
        self.refresh_digests()
        baseline = self.run_validator("--strict")
        self.assertEqual(baseline.returncode, 0, baseline.stdout + baseline.stderr)
        spec.write_text(spec.read_text(encoding="utf-8").replace("Chosen option: option-a", "Chosen option: option-b"), encoding="utf-8")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("decision-digest-mismatch", result.stdout)

    def test_per_task_subject_digest_maps_to_final_candidate(self) -> None:
        acceptance = self.root / "reviews" / "acceptance.md"
        acceptance.write_text(
            acceptance.read_text(encoding="utf-8").replace(
                f"Subject revision: sha256:{CANDIDATE}",
                "Subject revision: sha256:" + "c" * 64,
            ),
            encoding="utf-8",
        )
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_multimilestone_base_must_equal_prior_acceptance(self) -> None:
        self.extend_standard_to_m2()
        baseline = self.run_validator("--strict")
        self.assertEqual(baseline.returncode, 0, baseline.stdout + baseline.stderr)
        plan2 = self.root / "plans" / "M2-plan.md"
        plan2.write_text(plan2.read_text(encoding="utf-8").replace("Base revision: sha256:" + "c" * 64, "Base revision: sha256:" + "d" * 64), encoding="utf-8")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("milestone-continuity-mismatch", result.stdout)

    def test_draft_spec_and_plan_cannot_deliver(self) -> None:
        self.convert_to_standard_m1()
        spec = self.root / "spec.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("Spec status: reviewed", "Spec status: draft"), encoding="utf-8")
        plan = self.root / "plans" / "M1-plan.md"
        plan.write_text(plan.read_text(encoding="utf-8").replace("Plan status: accepted", "Plan status: draft"), encoding="utf-8")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("spec-not-reviewed", result.stdout)
        self.assertIn("plan-not-accepted", result.stdout)

    def test_success_state_cannot_retain_blockers(self) -> None:
        state = self.root / "workflow-state.md"
        state.write_text(state.read_text(encoding="utf-8").replace("Current blocker: none", "Current blocker: permission"), encoding="utf-8")
        change = self.root / "change.md"
        change.write_text(change.read_text(encoding="utf-8").replace("Blocker: none", "Blocker: external"), encoding="utf-8")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("contradictory-workflow-blocker", result.stdout)
        self.assertIn("contradictory-task-blocker", result.stdout)

    def test_not_applicable_evidence_cannot_satisfy_delivery(self) -> None:
        self.write_acceptance(self.evidence_block(outcome="not-applicable"))
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ac-without-evidence", result.stdout)

    def test_current_failed_evidence_cannot_complete_task(self) -> None:
        self.write_acceptance(self.evidence_block(outcome="failed"))
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("current-evidence-not-passing", result.stdout)
        self.assertIn("completed-task-contradicted", result.stdout)

    def test_stale_failed_history_is_allowed_when_current_pass_exists(self) -> None:
        evidence = self.evidence_block("EVID-001", outcome="failed", freshness="stale")
        evidence += "\n" + self.evidence_block("EVID-002")
        self.write_acceptance(evidence)
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_evidence_class_must_cover_task_and_acceptance(self) -> None:
        self.write_acceptance(self.evidence_block(verification_class="runtime"))
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing-evidence-class", result.stdout)

    def test_review_fingerprint_change_is_rejected(self) -> None:
        review = self.root / "reviews" / "code-review-M1.md"
        review.write_text(review.read_text(encoding="utf-8").replace("Repository fingerprint after: sha256:" + "b" * 64, "Repository fingerprint after: sha256:" + "d" * 64), encoding="utf-8")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("review-mutated-inputs", result.stdout)

    def test_preexisting_index_forces_user_managed_policy(self) -> None:
        state = self.root / "workflow-state.md"
        content = state.read_text(encoding="utf-8")
        content = content.replace("Commit policy: user-managed", "Commit policy: auto")
        content = content.replace("Initial staged paths: none", "Initial staged paths: user-change.py")
        state.write_text(content, encoding="utf-8")
        result = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("preexisting-index", result.stdout)

    def test_dirty_owned_overlap_is_rejected_for_auto_commit(self) -> None:
        state = self.root / "workflow-state.md"
        content = state.read_text(encoding="utf-8")
        content = content.replace("Commit policy: user-managed", "Commit policy: auto")
        content = content.replace("Initial dirty paths: none", "Initial dirty paths: src/example.py")
        state.write_text(content, encoding="utf-8")
        result = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("dirty-owned-overlap", result.stdout)

    def test_dirty_owned_ancestor_overlap_is_rejected(self) -> None:
        state = self.root / "workflow-state.md"
        content = state.read_text(encoding="utf-8")
        content = content.replace("Commit policy: user-managed", "Commit policy: auto")
        content = content.replace("Initial dirty paths: none", "Initial dirty paths: src/example.py")
        content = content.replace("Owned paths: src/example.py", "Owned paths: ./src")
        state.write_text(content, encoding="utf-8")
        result = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("dirty-owned-overlap", result.stdout)

    def test_confirmation_metadata_cannot_be_predeclared(self) -> None:
        change = self.root / "change.md"
        content = change.read_text(encoding="utf-8")
        content = content.replace("Requirements status: confirmed", "Requirements status: draft")
        change.write_text(content, encoding="utf-8")
        result = self.run_validator()
        self.assertEqual(result.returncode, 1)
        self.assertIn("premature-confirmation", result.stdout)

    def test_artifact_hash_is_checked(self) -> None:
        artifacts = self.root / "artifacts"
        artifacts.mkdir()
        report = artifacts / "report.txt"
        report.write_text("verified\n", encoding="utf-8")
        digest = hashlib.sha256(report.read_bytes()).hexdigest()
        self.write_acceptance(self.evidence_block(artifacts=f"`artifacts/report.txt` (sha256:{digest})"))
        self.assertEqual(self.run_validator("--strict").returncode, 0)
        report.write_text("changed\n", encoding="utf-8")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("artifact-digest-mismatch", result.stdout)

    def test_secret_detection_does_not_echo_secret(self) -> None:
        secret = "sk-" + "A" * 32
        with (self.root / "workflow-state.md").open("a", encoding="utf-8") as handle:
            handle.write(f"\nUnsafe value: {secret}\n")
        result = self.run_validator("--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertTrue(any(issue["code"] == "possible-secret" for issue in payload["issues"]))
        self.assertNotIn(secret, result.stdout)

    def test_secret_in_echoed_control_field_is_redacted(self) -> None:
        secret = "sk-" + "B" * 32
        state = self.root / "workflow-state.md"
        state.write_text(state.read_text(encoding="utf-8").replace("Rigor: lite", f"Rigor: {secret}"), encoding="utf-8")
        result = self.run_validator("--json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid-profile", result.stdout)
        self.assertNotIn(secret, result.stdout)

    def test_strict_rejects_empty_traceability(self) -> None:
        (self.root / "change.md").write_text(
            f"""# Lite Change Contract: sample

- Requirements status: confirmed
- Confirmed by: originating user request
- Confirmed at: 2026-08-03T11:00:00Z
- Confirmed revision: sha256:{BASE}
- Technical options status: not-applicable
- Base revision: sha256:{BASE}
- Candidate revision: sha256:{CANDIDATE}
- Reviewed revision: sha256:{CANDIDATE}
- Accepted revision: sha256:{CANDIDATE}
- Release revision: not-applicable
- Deployed revision: not-applicable
""",
            encoding="utf-8",
        )
        (self.root / "reviews" / "acceptance.md").write_text(
            f"""# Acceptance and Evidence: sample

- Acceptance status: accepted
- Delivery target: implemented
- Base revision: sha256:{BASE}
- Candidate revision: sha256:{CANDIDATE}
- Reviewed revision: sha256:{CANDIDATE}
- Accepted revision: sha256:{CANDIDATE}
- Release revision: not-applicable
- Deployed revision: not-applicable
""",
            encoding="utf-8",
        )
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("empty-traceability", result.stdout)

    def test_significant_recorded_decision_cannot_bypass_confirmation(self) -> None:
        change = self.root / "change.md"
        with change.open("a", encoding="utf-8") as handle:
            handle.write(
                """
## DEC-001 — Significant choice

- Significant option: yes
- Status: recorded
- Chosen option: option-a
- Confirmed by: none
- Confirmed at: none
- Confirmed revision: none
"""
            )
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("decision-unconfirmed", result.stdout)

    def test_indented_significant_decision_is_active(self) -> None:
        change = self.root / "change.md"
        with change.open("a", encoding="utf-8") as handle:
            handle.write(
                """
   ## DEC-001 — Indented significant choice

   - Significant option: yes
   - Status: recorded
   - Chosen option: option-a
   - Confirmed by: none
   - Confirmed at: none
   - Confirmed revision: none
"""
            )
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("decision-unconfirmed", result.stdout)

    def test_duplicate_authoritative_field_is_rejected(self) -> None:
        state = self.root / "workflow-state.md"
        with state.open("a", encoding="utf-8") as handle:
            handle.write("\n- Delivery target: deployed\n")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate-authoritative-field", result.stdout)

    def test_markdown_symlink_is_rejected_without_following(self) -> None:
        state = self.root / "workflow-state.md"
        outside = Path(self.tempdir.name) / "outside-state.md"
        outside.write_bytes(state.read_bytes())
        state.unlink()
        state.symlink_to(outside)
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot safely read", result.stderr)

    def test_lite_cannot_hide_m2_behind_m1_review(self) -> None:
        state = self.root / "workflow-state.md"
        state.write_text(state.read_text(encoding="utf-8").replace("Current milestone: M1", "Current milestone: M2"), encoding="utf-8")
        change = self.root / "change.md"
        change.write_text(change.read_text(encoding="utf-8").replace("TASK-M1-001", "TASK-M2-001"), encoding="utf-8")
        acceptance = self.root / "reviews" / "acceptance.md"
        acceptance.write_text(acceptance.read_text(encoding="utf-8").replace("TASK-M1-001", "TASK-M2-001"), encoding="utf-8")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("lite-multiple-milestones", result.stdout)

    def test_standard_m2_requires_matching_plan_and_code_reviews(self) -> None:
        state = self.root / "workflow-state.md"
        state.write_text(
            state.read_text(encoding="utf-8")
            .replace("Rigor: lite", "Rigor: standard")
            .replace("Rigor rationale: Low-risk reversible single-domain change.", "Rigor rationale: Cross-module standard fixture.")
            .replace("Current milestone: M1", "Current milestone: M2"),
            encoding="utf-8",
        )
        (self.root / "change.md").unlink()
        (self.root / "requirements.md").write_text(
            f"""# Requirements: sample
- Requirements status: confirmed
- Confirmed by: originating user request
- Confirmed at: 2026-08-03T11:00:00Z
- Confirmed revision: sha256:{BASE}

## REQ-001 — Return a stable value
- Statement: The public function returns the documented value.
""",
            encoding="utf-8",
        )
        (self.root / "spec.md").write_text(
            f"""# Specification: sample
- Spec status: reviewed
- Requirements revision: sha256:{BASE}
- Technical options status: not-applicable
- Options confirmed by: none
- Options confirmed at: none
- Options confirmed revision: none

## AC-001 — Stable value is observed
- Requirements: REQ-001
- Verification class: unit
- Method: Focused unit test.
- Passing condition: The assertion passes.
""",
            encoding="utf-8",
        )
        plans = self.root / "plans"
        plans.mkdir()
        (plans / "M1-plan.md").write_text(
            f"""# Milestone Plan M1
- Plan status: accepted
- Spec revision: sha256:{BASE}
- Base revision: sha256:{BASE}
- Candidate revision: sha256:{BASE}
- Reviewed revision: sha256:{BASE}
- Accepted revision: sha256:{BASE}
- Release revision: not-applicable
- Deployed revision: not-applicable
""",
            encoding="utf-8",
        )
        (plans / "M2-plan.md").write_text(
            f"""# Milestone Plan M2
- Plan status: accepted
- Spec revision: sha256:{BASE}
- Base revision: sha256:{BASE}
- Candidate revision: sha256:{CANDIDATE}
- Reviewed revision: sha256:{CANDIDATE}
- Accepted revision: sha256:{CANDIDATE}
- Release revision: not-applicable
- Deployed revision: not-applicable

## TASK-M2-001 — Implement the stable value
- Status: completed
- Acceptance: AC-001
- Verification class: unit
- Dependencies: none
- Owned paths: src/example.py
- Blocker: none
- Resume condition: none
""",
            encoding="utf-8",
        )
        acceptance = self.root / "reviews" / "acceptance.md"
        acceptance.write_text(acceptance.read_text(encoding="utf-8").replace("TASK-M1-001", "TASK-M2-001"), encoding="utf-8")
        review_path = self.root / "reviews" / "code-review-M1.md"
        review_path.write_text(review_path.read_text(encoding="utf-8").replace("Rigor: lite", "Rigor: standard"), encoding="utf-8")
        review = review_path.read_text(encoding="utf-8")
        (self.root / "reviews" / "spec-review.md").write_text(review, encoding="utf-8")
        (self.root / "reviews" / "plan-review-M1.md").write_text(review, encoding="utf-8")
        self.refresh_digests()
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("plan-review-M2.md", result.stdout)
        self.assertIn("code-review-M2.md", result.stdout)

    def test_deployed_target_requires_release_smoke_evidence(self) -> None:
        state = self.root / "workflow-state.md"
        state.write_text(state.read_text(encoding="utf-8").replace("Delivery target: implemented", "Delivery target: deployed").replace("Workflow status: implemented", "Workflow status: deployed"), encoding="utf-8")
        acceptance = self.root / "reviews" / "acceptance.md"
        acceptance.write_text(acceptance.read_text(encoding="utf-8").replace("Delivery target: implemented", "Delivery target: deployed").replace("Release revision: not-applicable", f"Release revision: sha256:{CANDIDATE}").replace("Deployed revision: not-applicable", f"Deployed revision: sha256:{CANDIDATE}"), encoding="utf-8")
        change = self.root / "change.md"
        change.write_text(change.read_text(encoding="utf-8").replace("Release revision: not-applicable", f"Release revision: sha256:{CANDIDATE}").replace("Deployed revision: not-applicable", f"Deployed revision: sha256:{CANDIDATE}"), encoding="utf-8")
        (self.root / "release-plan.md").write_text(
            f"""# Release Plan
- Status: deployed
- Delivery target: deployed
- Candidate revision: sha256:{CANDIDATE}
- Release revision: sha256:{CANDIDATE}
- Deployed revision: sha256:{CANDIDATE}
- Release authority: principal=user; approval=RELEASE-1
""",
            encoding="utf-8",
        )
        missing = self.run_validator("--strict")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("missing-post-deploy-evidence", missing.stdout)
        self.assertIn("missing-external-operation-ledger", missing.stdout)

        with acceptance.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n"
                + self.evidence_block(
                    "EVID-002",
                    verification_class="release",
                    authorization="principal=user; approval=RELEASE-1",
                )
            )
        self.append_deployment_ledger()
        passing = self.run_validator("--strict")
        self.assertEqual(passing.returncode, 0, passing.stdout + passing.stderr)

    def test_deployed_cross_file_revision_mismatch_is_rejected(self) -> None:
        state = self.root / "workflow-state.md"
        state.write_text(state.read_text(encoding="utf-8").replace("Delivery target: implemented", "Delivery target: deployed").replace("Workflow status: implemented", "Workflow status: deployed"), encoding="utf-8")
        acceptance = self.root / "reviews" / "acceptance.md"
        acceptance.write_text(
            acceptance.read_text(encoding="utf-8")
            .replace("Delivery target: implemented", "Delivery target: deployed")
            .replace("Release revision: not-applicable", f"Release revision: sha256:{CANDIDATE}")
            .replace("Deployed revision: not-applicable", f"Deployed revision: sha256:{CANDIDATE}")
            + "\n"
            + self.evidence_block(
                "EVID-002",
                verification_class="release",
                authorization="principal=user; approval=RELEASE-2",
            ),
            encoding="utf-8",
        )
        change = self.root / "change.md"
        change.write_text(change.read_text(encoding="utf-8").replace("Release revision: not-applicable", f"Release revision: sha256:{CANDIDATE}").replace("Deployed revision: not-applicable", f"Deployed revision: sha256:{CANDIDATE}"), encoding="utf-8")
        other = "d" * 64
        (self.root / "release-plan.md").write_text(
            f"""# Release Plan
- Status: deployed
- Delivery target: deployed
- Candidate revision: sha256:{other}
- Release revision: sha256:{other}
- Deployed revision: sha256:{other}
- Release authority: principal=user; approval=RELEASE-2
""",
            encoding="utf-8",
        )
        self.append_deployment_ledger("RELEASE-2", other)
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("release-revision-mismatch", result.stdout)

    def test_deployed_evidence_authorization_must_match_release_authority(self) -> None:
        self.configure_complete_deployment(evidence_authorization="different approval")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("release-evidence-authorization-mismatch", result.stdout)

    def test_deployed_cannot_retain_prepared_operation(self) -> None:
        self.configure_complete_deployment(ledger_state="prepared")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unresolved-external-operation", result.stdout)
        self.assertIn("missing-observed-deployment-operation", result.stdout)

    def test_deployed_rejects_generic_release_authority(self) -> None:
        for authority in ("authorized", "principal=   ; approval=---"):
            with self.subTest(authority=authority):
                self.configure_complete_deployment(
                    release_authority=authority,
                    evidence_authorization=authority,
                )
                result = self.run_validator("--strict")
                self.assertEqual(result.returncode, 1)
                self.assertIn("missing-release-authority", result.stdout)
                self.write_valid_lite()

    def test_deployed_rejects_arbitrary_ledger_state(self) -> None:
        self.configure_complete_deployment(ledger_state="executing")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid-external-operation-state", result.stdout)

    def test_deployed_rejects_malformed_ledger_row(self) -> None:
        self.configure_complete_deployment()
        with (self.root / "workflow-state.md").open("a", encoding="utf-8") as handle:
            handle.write("| malformed | row |\n")
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing-external-operation-ledger", result.stdout)

    def test_deployed_rejects_incomplete_leftover_ledger_row(self) -> None:
        self.configure_complete_deployment()
        with (self.root / "workflow-state.md").open("a", encoding="utf-8") as handle:
            handle.write(
                f"| none | none | sha256:{CANDIDATE} | none | none | observed | none | EVID-002 |\n"
            )
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("incomplete-external-operation-row", result.stdout)

    def test_deployed_rejects_second_ledger_table(self) -> None:
        self.configure_complete_deployment()
        with (self.root / "workflow-state.md").open("a", encoding="utf-8") as handle:
            handle.write(
                f"""

| Operation ID / idempotency key | Target and intended effect | Subject revision | Pre-state | Rollback/recovery | State | Recovery query | Result evidence |
|---|---|---|---|---|---|---|---|
| RELEASE-LEFTOVER | production deployment | sha256:{CANDIDATE} | prior revision | redeploy prior | prepared | query deployment | not-run |
"""
            )
        result = self.run_validator("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing-external-operation-ledger", result.stdout)

    def test_missing_root_returns_usage_error(self) -> None:
        missing = Path(self.tempdir.name) / "missing"
        result = self.run_validator(root=missing)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
