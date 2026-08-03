#!/usr/bin/env python3
"""Create a non-destructive spec-driven-dev initiative scaffold."""

from __future__ import annotations

import argparse
import os
import re
import secrets
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "templates"

PROFILE_FILES: dict[str, list[tuple[str, str, dict[str, str]]]] = {
    "lite": [
        ("workflow-state.md", "workflow-state.md", {}),
        ("change.md", "change.md", {}),
        ("review.md", "reviews/code-review-M1.md", {"REVIEW_KIND": "Code Review M1"}),
        ("acceptance.md", "reviews/acceptance.md", {}),
    ],
    "standard": [
        ("workflow-state.md", "workflow-state.md", {}),
        ("requirements.md", "requirements.md", {}),
        ("spec.md", "spec.md", {}),
        ("milestone-plan.md", "plans/M1-plan.md", {"MILESTONE": "M1"}),
        ("review.md", "reviews/spec-review.md", {"REVIEW_KIND": "Specification Review"}),
        ("review.md", "reviews/plan-review-M1.md", {"REVIEW_KIND": "Plan Review M1"}),
        ("review.md", "reviews/code-review-M1.md", {"REVIEW_KIND": "Code Review M1"}),
        ("acceptance.md", "reviews/acceptance.md", {}),
    ],
    "high-assurance": [
        ("workflow-state.md", "workflow-state.md", {}),
        ("requirements.md", "requirements.md", {}),
        ("spec.md", "spec.md", {}),
        ("milestone-plan.md", "plans/M1-plan.md", {"MILESTONE": "M1"}),
        ("review.md", "reviews/spec-review.md", {"REVIEW_KIND": "Specification Review"}),
        ("review.md", "reviews/plan-review-M1.md", {"REVIEW_KIND": "Plan Review M1"}),
        ("review.md", "reviews/code-review-M1.md", {"REVIEW_KIND": "Code Review M1"}),
        ("acceptance.md", "reviews/acceptance.md", {}),
        ("release-plan.md", "release-plan.md", {}),
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create profile-specific spec-driven-dev artifacts without overwriting files."
    )
    parser.add_argument("project_root", type=Path)
    parser.add_argument("initiative", help="Lowercase hyphenated initiative slug")
    parser.add_argument("--profile", choices=sorted(PROFILE_FILES), default="standard")
    parser.add_argument(
        "--commit-policy",
        choices=("auto", "checkpoint", "user-managed"),
        default="user-managed",
    )
    parser.add_argument(
        "--delivery-target",
        choices=("implemented", "release-ready", "deployed"),
        default="implemented",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        help="Path relative to project root; defaults to docs/specs/<initiative>",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Create missing files in an existing target; never overwrite files.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def validate_slug(value: str) -> None:
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) is None:
        raise ValueError("initiative must use lowercase letters/digits separated by single hyphens")


def run_git(project_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def git_paths(project_root: Path, *args: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", *args, "-z"],
            cwd=project_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []
    return sorted(item.decode("utf-8", errors="surrogateescape") for item in result.stdout.split(b"\0") if item)


def format_paths(paths: list[str]) -> str:
    return ", ".join(paths) if paths else "none"


def repository_state(project_root: Path) -> dict[str, str]:
    inside_worktree = run_git(project_root, "rev-parse", "--is-inside-work-tree")
    if inside_worktree != "true":
        return {
            "REPOSITORY_KIND": "unversioned",
            "BASE_REVISION": "unversioned",
            "BRANCH": "none",
            "STAGED_PATHS": "none",
            "UNSTAGED_PATHS": "none",
            "UNTRACKED_PATHS": "none",
            "DIRTY_PATHS": "none",
        }

    base = run_git(project_root, "rev-parse", "HEAD")
    branch = run_git(project_root, "branch", "--show-current") or run_git(
        project_root, "symbolic-ref", "--short", "HEAD"
    ) or "detached"
    staged = git_paths(project_root, "diff", "--cached", "--name-only")
    unstaged = git_paths(project_root, "diff", "--name-only")
    untracked = git_paths(project_root, "ls-files", "--others", "--exclude-standard")
    dirty = sorted(set(staged + unstaged + untracked))
    return {
        "REPOSITORY_KIND": "git",
        "BASE_REVISION": f"git:{base}" if base is not None else "git:unborn",
        "BRANCH": branch,
        "STAGED_PATHS": format_paths(staged),
        "UNSTAGED_PATHS": format_paths(unstaged),
        "UNTRACKED_PATHS": format_paths(untracked),
        "DIRTY_PATHS": format_paths(dirty),
    }


def resolve_target(project_root: Path, initiative: str, artifact_root: Path | None) -> Path:
    candidate = artifact_root or Path("docs") / "specs" / initiative
    target = candidate if candidate.is_absolute() else project_root / candidate
    target = target.resolve()
    try:
        target.relative_to(project_root)
    except ValueError as exc:
        raise ValueError("artifact root must stay inside project root") from exc
    return target


def reject_symlink_components(path: Path, project_root: Path) -> None:
    try:
        relative = path.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {path}") from exc
    current = project_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"artifact path contains a symlink component: {current}")


def assert_destination_boundary(path: Path, project_root: Path, target: Path) -> None:
    reject_symlink_components(path, project_root)
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(project_root)
        resolved.relative_to(target)
    except ValueError as exc:
        raise ValueError(f"artifact destination escapes target: {path}") from exc


def directory_flags() -> int:
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise OSError("this platform lacks secure no-follow directory operations")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def open_relative_directory(root_fd: int, parts: tuple[str, ...], *, create: bool) -> int:
    current_fd = os.dup(root_fd)
    try:
        for part in parts:
            if part in {"", ".", ".."} or "/" in part:
                raise ValueError(f"unsafe path component: {part!r}")
            try:
                next_fd = os.open(part, directory_flags(), dir_fd=current_fd)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, mode=0o755, dir_fd=current_fd)
                except FileExistsError:
                    pass
                next_fd = os.open(part, directory_flags(), dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def open_target_directory(project_root: Path, target: Path, *, create: bool) -> int:
    relative = target.relative_to(project_root)
    project_fd = os.open(project_root, directory_flags())
    try:
        return open_relative_directory(project_fd, relative.parts, create=create)
    finally:
        os.close(project_fd)


def stat_relative_file(target_fd: int, relative: Path) -> os.stat_result:
    parent_fd = open_relative_directory(target_fd, relative.parts[:-1], create=False)
    try:
        return os.stat(relative.name, dir_fd=parent_fd, follow_symlinks=False)
    finally:
        os.close(parent_fd)


def create_relative_file(target_fd: int, relative: Path, content: str) -> None:
    parent_fd = open_relative_directory(target_fd, relative.parts[:-1], create=True)
    file_fd: int | None = None
    try:
        file_fd = os.open(
            relative.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o644,
            dir_fd=parent_fd,
        )
        with os.fdopen(file_fd, "w", encoding="utf-8") as handle:
            file_fd = None
            handle.write(content)
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(parent_fd)


def render(template_name: str, values: dict[str, str]) -> str:
    template_path = TEMPLATE_ROOT / template_name
    if not template_path.is_file():
        raise FileNotFoundError(f"missing bundled template: {template_path}")
    content = template_path.read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace("{{" + key + "}}", value)
    unresolved = sorted(
        token.split("}}", 1)[0]
        for token in content.split("{{")[1:]
        if "}}" in token
    )
    if unresolved:
        raise ValueError(f"unresolved template values in {template_name}: {', '.join(unresolved)}")
    return content


def main() -> int:
    args = parse_args()
    try:
        validate_slug(args.initiative)
        project_root = args.project_root.resolve(strict=True)
        if not project_root.is_dir():
            raise ValueError("project_root must be a directory")
        target = resolve_target(project_root, args.initiative, args.artifact_root)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        if target.exists() and not target.is_dir():
            print(f"error: target exists but is not a directory: {target}", file=sys.stderr)
            return 2
        if target.exists() and any(target.iterdir()) and not args.merge:
            print(
                f"error: target is not empty: {target}; use --merge to add only missing files",
                file=sys.stderr,
            )
            return 2
    except OSError as exc:
        print(f"error: cannot inspect target {target}: {exc}", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    state = repository_state(project_root)
    try:
        artifact_display = target.relative_to(project_root).as_posix()
    except ValueError:
        artifact_display = str(target)
    common = {
        "INITIATIVE": args.initiative,
        "RUN_ID": f"SDD-{now.replace(':', '').replace('-', '')}-{secrets.token_hex(3)}",
        "ARTIFACT_ROOT": artifact_display,
        "PROFILE": args.profile,
        "COMMIT_POLICY": args.commit_policy,
        "DELIVERY_TARGET": args.delivery_target,
        "TECHNICAL_OPTIONS_STATUS": "not-applicable" if args.profile == "lite" else "awaiting-confirmation",
        "CREATED_AT": now,
        "MILESTONE": "M1",
        "REVIEW_KIND": "Review",
        **state,
    }

    profile_files = list(PROFILE_FILES[args.profile])
    if args.delivery_target != "implemented" and not any(item[1] == "release-plan.md" for item in profile_files):
        profile_files.append(("release-plan.md", "release-plan.md", {}))

    directories = [target, target / "spikes", target / "amendments", target / "reviews"]
    if args.profile != "lite":
        directories.append(target / "plans")

    writes: list[tuple[Path, str]] = []
    skipped: list[Path] = []
    try:
        for template_name, relative_destination, extra in profile_files:
            destination = target / relative_destination
            assert_destination_boundary(destination, project_root, target)
            if destination.exists() or destination.is_symlink():
                if args.merge:
                    if destination.is_symlink() or not destination.is_file():
                        raise ValueError(f"merge can preserve only a regular file: {destination}")
                    skipped.append(destination)
                    continue
                print(f"error: refusing to overwrite {destination}", file=sys.stderr)
                return 2
            writes.append((destination, render(template_name, {**common, **extra})))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(f"target: {target}")
        for directory in directories:
            print(f"mkdir: {directory}")
        for destination, _ in writes:
            print(f"create: {destination}")
        for destination in skipped:
            print(f"skip-existing: {destination}")
        return 0

    target_fd: int | None = None
    try:
        target_fd = open_target_directory(project_root, target, create=True)
        if os.listdir(target_fd) and not args.merge:
            raise ValueError(f"target became non-empty before creation: {target}")
        for directory in directories:
            assert_destination_boundary(directory, project_root, target)
            relative = directory.relative_to(target)
            if relative.parts:
                directory_fd = open_relative_directory(target_fd, relative.parts, create=True)
                os.close(directory_fd)
        for destination in skipped:
            relative = destination.relative_to(target)
            metadata = stat_relative_file(target_fd, relative)
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError(f"merge can preserve only a regular file: {destination}")
        for destination, content in writes:
            assert_destination_boundary(destination, project_root, target)
            create_relative_file(target_fd, destination.relative_to(target), content)
    except (OSError, ValueError) as exc:
        print(f"error: refusing unsafe/overwriting artifact creation: {exc}", file=sys.stderr)
        return 2
    finally:
        if target_fd is not None:
            os.close(target_fd)

    print(f"created initiative scaffold: {target}")
    for destination, _ in writes:
        print(f"created: {destination.relative_to(project_root)}")
    for destination in skipped:
        print(f"preserved: {destination.relative_to(project_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
