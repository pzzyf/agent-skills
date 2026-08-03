from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "scaffold_artifacts.py"
VALIDATOR = SKILL_ROOT / "scripts" / "validate_traceability.py"


class ScaffoldArtifactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "project"
        self.project.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.project), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def files_for(self, initiative: str) -> set[str]:
        root = self.project / "docs" / "specs" / initiative
        return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}

    def test_profiles_create_exact_core_files(self) -> None:
        expected = {
            "lite": {
                "workflow-state.md",
                "change.md",
                "reviews/code-review-M1.md",
                "reviews/acceptance.md",
            },
            "standard": {
                "workflow-state.md",
                "requirements.md",
                "spec.md",
                "plans/M1-plan.md",
                "reviews/spec-review.md",
                "reviews/plan-review-M1.md",
                "reviews/code-review-M1.md",
                "reviews/acceptance.md",
            },
            "high-assurance": {
                "workflow-state.md",
                "requirements.md",
                "spec.md",
                "plans/M1-plan.md",
                "reviews/spec-review.md",
                "reviews/plan-review-M1.md",
                "reviews/code-review-M1.md",
                "reviews/acceptance.md",
                "release-plan.md",
            },
        }
        for profile, file_set in expected.items():
            initiative = profile
            result = self.run_script(initiative, "--profile", profile)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.files_for(initiative), file_set)

    def test_fresh_profile_scaffolds_have_no_structural_errors(self) -> None:
        for profile in ("lite", "standard", "high-assurance"):
            initiative = f"valid-{profile}"
            created = self.run_script(initiative, "--profile", profile)
            self.assertEqual(created.returncode, 0, created.stderr)
            root = self.project / "docs" / "specs" / initiative
            checked = subprocess.run(
                [sys.executable, str(VALIDATOR), str(root), "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertEqual(json.loads(checked.stdout)["errors"], 0)

    def test_numeric_slug_is_valid(self) -> None:
        result = self.run_script("feature-2", "--profile", "lite")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_release_target_adds_release_plan_for_standard(self) -> None:
        result = self.run_script(
            "release-candidate",
            "--profile",
            "standard",
            "--delivery-target",
            "release-ready",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("release-plan.md", self.files_for("release-candidate"))

    def test_dry_run_does_not_write(self) -> None:
        result = self.run_script("dry-run", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.project / "docs").exists())

    def test_nonempty_target_is_refused_and_merge_preserves_bytes(self) -> None:
        first = self.run_script("merge-check", "--profile", "lite")
        self.assertEqual(first.returncode, 0, first.stderr)
        change = self.project / "docs" / "specs" / "merge-check" / "change.md"
        original = b"user-owned-content\n"
        change.write_bytes(original)

        refused = self.run_script("merge-check", "--profile", "lite")
        self.assertEqual(refused.returncode, 2)
        merged = self.run_script("merge-check", "--profile", "lite", "--merge")
        self.assertEqual(merged.returncode, 0, merged.stderr)
        self.assertEqual(change.read_bytes(), original)

    def test_path_traversal_and_external_artifact_root_are_refused(self) -> None:
        invalid_slug = self.run_script("../escape")
        self.assertEqual(invalid_slug.returncode, 2)
        outside = Path(self.tempdir.name) / "outside"
        invalid_root = self.run_script("safe-slug", "--artifact-root", str(outside))
        self.assertEqual(invalid_root.returncode, 2)

    def test_symlink_artifact_component_is_refused(self) -> None:
        outside = Path(self.tempdir.name) / "outside"
        outside.mkdir()
        docs = self.project / "docs"
        docs.symlink_to(outside, target_is_directory=True)
        result = self.run_script("symlink-check", "--profile", "lite")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((outside / "specs" / "symlink-check").exists())

    def test_unborn_git_repository_preserves_index_baseline(self) -> None:
        subprocess.run(["git", "init"], cwd=self.project, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        staged = self.project / "user-staged.txt"
        staged.write_text("user content\n", encoding="utf-8")
        subprocess.run(["git", "add", "user-staged.txt"], cwd=self.project, check=True)
        result = self.run_script("unborn", "--profile", "lite", "--commit-policy", "auto")
        self.assertEqual(result.returncode, 0, result.stderr)
        state = (self.project / "docs" / "specs" / "unborn" / "workflow-state.md").read_text(encoding="utf-8")
        self.assertIn("Repository kind: git", state)
        self.assertIn("Base revision: git:unborn", state)
        self.assertIn("Initial staged paths: user-staged.txt", state)
        self.assertIn("Initial dirty paths: user-staged.txt", state)

    def test_merge_rejects_directory_at_required_file_path(self) -> None:
        target = self.project / "docs" / "specs" / "bad-merge"
        (target / "reviews" / "code-review-M1.md").mkdir(parents=True)
        result = self.run_script("bad-merge", "--profile", "lite", "--merge")
        self.assertEqual(result.returncode, 2)
        self.assertIn("regular file", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_target_file_returns_deterministic_usage_error(self) -> None:
        target = self.project / "docs" / "specs" / "target-file"
        target.parent.mkdir(parents=True)
        target.write_text("occupied\n", encoding="utf-8")
        result = self.run_script("target-file", "--profile", "lite")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_directory_descriptor_write_stays_anchored_after_path_swap(self) -> None:
        spec = importlib.util.spec_from_file_location("scaffold_under_test", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules["scaffold_under_test"] = module
        spec.loader.exec_module(module)

        target = self.project / "docs" / "specs" / "race-safe"
        target.mkdir(parents=True)
        target_fd = module.open_target_directory(self.project, target, create=False)
        try:
            reviews_fd = module.open_relative_directory(target_fd, ("reviews",), create=True)
            os.close(reviews_fd)
            anchored = target.with_name("race-safe-anchored")
            target.rename(anchored)
            outside = Path(self.tempdir.name) / "outside-race"
            outside.mkdir()
            target.symlink_to(outside, target_is_directory=True)
            module.create_relative_file(target_fd, Path("reviews/proof.md"), "anchored\n")
        finally:
            os.close(target_fd)
        self.assertEqual((anchored / "reviews" / "proof.md").read_text(encoding="utf-8"), "anchored\n")
        self.assertFalse((outside / "reviews" / "proof.md").exists())


if __name__ == "__main__":
    unittest.main()
