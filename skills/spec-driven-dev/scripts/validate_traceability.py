#!/usr/bin/env python3
"""Validate spec-driven-dev artifact structure and traceability."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass, asdict
from pathlib import Path, PurePosixPath


ID_PATTERN = re.compile(
    r"\b(?:REQ|RISK|SPIKE|DEC|AC|EVID|AMD)-\d{3}\b|\bTASK-M\d+-\d{3}\b"
)
DEFINITION_PATTERN = re.compile(
    r"^ {0,3}(#{2,6})\s+((?:REQ|RISK|SPIKE|DEC|AC|EVID|AMD)-\d{3}|TASK-M[1-9]\d*-\d{3})\s+(?:—|-)\s+.+$",
    re.MULTILINE,
)
HEADING_PATTERN = re.compile(r"^ {0,3}(#{1,6})\s+.+$", re.MULTILINE)
FIELD_PATTERN = re.compile(r"^ {0,3}- ([A-Za-z][A-Za-z0-9 /_-]+):\s*(.*)$", re.MULTILINE)
ISO_TIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$")
REVISION_PATTERN = re.compile(r"^(?:git:[0-9a-f]{7,64}|sha256:[0-9a-f]{64}|[0-9a-f]{7,64})$")
BASE_REVISION_PATTERN = re.compile(
    r"^(?:git:unborn|unversioned|git:[0-9a-f]{7,64}|sha256:[0-9a-f]{64}|[0-9a-f]{7,64})$"
)
RELEASE_AUTHORITY_PATTERN = re.compile(
    r"^principal=([^;\r\n]+);\s*approval=((?=[A-Za-z0-9._:/#-]{3,}$)(?=.*[0-9._:/#-])[A-Za-z0-9][A-Za-z0-9._:/#-]*)$"
)

ALLOWED_PROFILES = {"lite", "standard", "high-assurance"}
ALLOWED_COMMIT_POLICIES = {"auto", "checkpoint", "user-managed"}
ALLOWED_DELIVERY_TARGETS = {"implemented", "release-ready", "deployed"}
ALLOWED_WORKFLOW_STATES = {
    "draft",
    "requirements-confirmed",
    "options-confirmed",
    "specified",
    "planned",
    "executing",
    "verifying",
    "fixing",
    "reviewing",
    "accepting",
    "implemented",
    "release-ready",
    "deployed",
    "blocked-permission",
    "blocked-external",
    "cancelled",
    "accepted-risk",
}
ALLOWED_REVIEW_MODES = {"independent", "degraded", "blocked", "unassessed"}
ALLOWED_OPTIONS_STATES = {"unassessed", "awaiting-confirmation", "confirmed", "not-applicable"}
ALLOWED_TASK_STATES = {
    "pending",
    "implementing",
    "verifying",
    "fixing",
    "completed",
    "reopened",
    "blocked-permission",
    "blocked-external",
    "cancelled",
    "accepted-risk",
}
ALLOWED_FRESHNESS = {"current", "stale"}
ALLOWED_BLOCKERS = {"none", "permission", "external"}
ALLOWED_OUTCOMES = {"passed", "failed", "inconclusive", "not-run", "not-applicable", "accepted-risk"}
ALLOWED_VERIFICATION_CLASSES = {
    "unit",
    "characterization",
    "contract",
    "integration",
    "runtime",
    "api",
    "browser",
    "visual",
    "accessibility",
    "migration",
    "performance",
    "build",
    "static",
    "documentation",
    "spike",
    "observation",
    "release",
    "security",
    "data-quality",
    "not-applicable",
    "pending",
}
REQUIRED_EVIDENCE_FIELDS = {
    "Acceptance",
    "Task",
    "Outcome",
    "Freshness",
    "Blocker",
    "Verification class",
    "Subject revision",
    "Candidate mapping",
    "Recorded at",
    "Environment",
    "Method",
    "Exit code",
    "Expected",
    "Actual",
    "Artifacts",
    "Sanitization",
    "Cleanup",
    "Invalidation",
    "Authorization",
    "Risk scope",
    "Risk impact",
    "Risk owner",
    "Risk expiry/revisit",
}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    "OpenAI-style token": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "credential-bearing URL": re.compile(r"https?://[^\s/:]+:[^\s/@]+@[^\s]+"),
}
TEMPLATE_CUE_PATTERN = re.compile(
    r"\[(?:replace|describe|write|name|record|map|pending|select|state|one |strongest|"
    r"observable|exact|use only|processes|inputs|environment|commands|command|"
    r"after explicit|implemented|repository|explicit|why |how )",
    re.IGNORECASE,
)
BRACKET_PLACEHOLDER_PATTERN = re.compile(r"\[(?![ xX]\])[^\]\n]+\](?!\s*\()")


@dataclass
class Issue:
    level: str
    code: str
    message: str
    path: str | None = None


@dataclass
class Definition:
    identifier: str
    path: Path
    line: int
    block: str
    fields: dict[str, str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate spec-driven-dev artifacts.")
    parser.add_argument("initiative_root", type=Path)
    parser.add_argument("--strict", action="store_true", help="Require a completed delivery state.")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--print-digests",
        action="store_true",
        help="Print canonical requirement/decision/spec/review digests and exit.",
    )
    return parser.parse_args()


def parse_fields(content: str) -> dict[str, str]:
    return {match.group(1).strip(): match.group(2).strip() for match in FIELD_PATTERN.finditer(content)}


def authoritative_fields(
    content: str,
    path: Path,
    names: set[str],
    issues: list[Issue],
    *,
    top_only: bool = True,
) -> dict[str, str]:
    """Read singleton control fields without last-value-wins ambiguity."""
    active_content = strip_fenced_code(content)
    matches = list(FIELD_PATTERN.finditer(active_content))
    first_section = re.search(r"(?m)^ {0,3}##\s+", active_content)
    header_end = first_section.start() if first_section else len(active_content)
    values: dict[str, str] = {}
    for name in sorted(names):
        found = [match for match in matches if match.group(1).strip() == name]
        if len(found) > 1:
            add_issue(
                issues,
                "error",
                "duplicate-authoritative-field",
                f"authoritative field {name!r} appears more than once",
                path,
            )
        if not found:
            continue
        if top_only and found[0].start() >= header_end:
            add_issue(
                issues,
                "error",
                "misplaced-authoritative-field",
                f"authoritative field {name!r} must be in the document header",
                path,
            )
        values[name] = found[0].group(2).strip()
    return values


def strip_fenced_code(content: str) -> str:
    """Blank CommonMark fenced blocks and HTML comments while preserving line numbers."""
    lines = content.splitlines(keepends=True)
    output: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    opening = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)$")
    for line in lines:
        body = line.rstrip("\r\n")
        newline = line[len(body):]
        if fence_character is None:
            match = opening.match(body)
            if match:
                marker = match.group(1)
                if marker[0] == "`" and "`" in match.group(2):
                    output.append(line)
                    continue
                fence_character = marker[0]
                fence_length = len(marker)
                output.append(newline)
            else:
                output.append(line)
            continue
        closing = re.fullmatch(
            rf" {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*",
            body,
        )
        output.append(newline)
        if closing:
            fence_character = None
            fence_length = 0
    stripped = "".join(output)
    html_comment = re.compile(r"(?s)<!--.*?(?:-->|\Z)")
    return html_comment.sub(lambda match: "\n" * match.group(0).count("\n"), stripped)


def normalize_projection(content: str) -> str:
    lines = [line.rstrip() for line in content.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + ("\n" if lines else "")


def without_fields(content: str, excluded: set[str]) -> str:
    kept: list[str] = []
    for line in content.splitlines(keepends=True):
        match = FIELD_PATTERN.fullmatch(line.rstrip("\r\n"))
        if match and match.group(1).strip() in excluded:
            continue
        kept.append(line)
    return "".join(kept)


def level_two_section(content: str, heading: str) -> str:
    pattern = re.compile(rf"(?m)^ {{0,3}}##\s+{re.escape(heading)}\s*$")
    match = pattern.search(content)
    if not match:
        return ""
    end_match = re.search(r"(?m)^ {0,3}##\s+", content[match.end():])
    end = match.end() + end_match.start() if end_match else len(content)
    return content[match.start():end]


def markdown_table(content: str, heading: str) -> tuple[list[str], list[dict[str, str]]]:
    """Parse the sole pipe table in an active level-two section."""
    section = level_two_section(strip_fenced_code(content), heading)
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in section.splitlines():
        match = re.fullmatch(r" {0,3}\|(.*)\|[ \t]*", line)
        if match:
            current.append([cell.strip() for cell in match.group(1).split("|")])
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    if len(tables) != 1:
        return [], []
    table_lines = tables[0]
    if len(table_lines) < 2:
        return [], []
    headers = table_lines[0]
    if len(table_lines[1]) != len(headers) or not all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in table_lines[1]
    ):
        return [], []
    if any(len(cells) != len(headers) for cells in table_lines[2:]):
        return [], []
    rows = [dict(zip(headers, cells)) for cells in table_lines[2:]]
    return headers, rows


def sha256_revision(content: str) -> str:
    return "sha256:" + hashlib.sha256(normalize_projection(content).encode("utf-8")).hexdigest()


def first_field_values(content: str, names: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in FIELD_PATTERN.finditer(strip_fenced_code(content)):
        name = match.group(1).strip()
        if name in names and name not in result:
            result[name] = match.group(2).strip()
    return result


def ids(value: str) -> set[str]:
    return set(ID_PATTERN.findall(value))


def verification_classes(value: str) -> set[str]:
    return {item.strip().lower() for item in re.split(r"[,|]", value) if item.strip()}


def is_concrete_release_authority(value: str) -> bool:
    match = RELEASE_AUTHORITY_PATTERN.fullmatch(value.strip())
    if not match:
        return False
    placeholders = {"pending", "unknown", "none", "no", "not-applicable", "n/a", "yes", "authorized", "approved"}
    principal = match.group(1).strip()
    approval = match.group(2).strip()
    return (
        any(character.isalnum() for character in principal)
        and any(character.isalnum() for character in approval)
        and principal.lower() not in placeholders
        and approval.lower() not in placeholders
    )


def safe_read_under_root(root: Path, path: Path, *, binary: bool = False) -> str | bytes:
    """Open a regular file with no-follow checks on every relative component."""
    relative = path.relative_to(root)
    if not relative.parts:
        raise ValueError("empty relative path")
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts[:-1]:
            next_fd = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        try:
            if not stat.S_ISREG(os.fstat(file_fd).st_mode):
                raise ValueError(f"not a regular file: {relative.as_posix()}")
            with os.fdopen(file_fd, "rb", closefd=False) as handle:
                data = handle.read()
        finally:
            os.close(file_fd)
    finally:
        os.close(directory_fd)
    return data if binary else data.decode("utf-8")


def read_markdown(root: Path) -> dict[Path, str]:
    files: dict[Path, str] = {}
    for path in sorted(root.rglob("*.md")):
        if path.is_symlink() or path.is_file():
            content = safe_read_under_root(root, path)
            assert isinstance(content, str)
            files[path] = content
    return files


def is_archived_review(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return len(relative.parts) >= 3 and relative.parts[:2] == ("reviews", "history")


def collect_definitions(files: dict[Path, str]) -> tuple[dict[str, Definition], list[Issue]]:
    definitions: dict[str, Definition] = {}
    issues: list[Issue] = []
    for path, raw_content in files.items():
        content = strip_fenced_code(raw_content)
        matches = list(DEFINITION_PATTERN.finditer(content))
        for match in matches:
            identifier = match.group(2)
            level = len(match.group(1))
            end = len(content)
            for heading in HEADING_PATTERN.finditer(content, match.end()):
                if len(heading.group(1)) <= level:
                    end = heading.start()
                    break
            block = content[match.start():end]
            line = content.count("\n", 0, match.start()) + 1
            if identifier in definitions:
                original = definitions[identifier]
                issues.append(
                    Issue(
                        "error",
                        "duplicate-id",
                        f"{identifier} is defined more than once; first at {original.path}:{original.line}",
                        f"{path}:{line}",
                    )
                )
                continue
            field_matches = list(FIELD_PATTERN.finditer(block))
            field_names = [field.group(1).strip() for field in field_matches]
            for duplicate in sorted({name for name in field_names if field_names.count(name) > 1}):
                issues.append(
                    Issue(
                        "error",
                        "duplicate-field",
                        f"{identifier} defines field {duplicate!r} more than once",
                        f"{path}:{line}",
                    )
                )
            definitions[identifier] = Definition(identifier, path, line, block, parse_fields(block))
    return definitions, issues


def requirements_projection(
    root: Path,
    profile: str,
    files: dict[Path, str],
    definitions: dict[str, Definition],
) -> str:
    if profile == "lite":
        path = root / "change.md"
        content = strip_fenced_code(files.get(path, ""))
        parts = [level_two_section(content, "Goal and Non-Goals")]
        parts.extend(
            definition.block
            for definition in sorted(definitions.values(), key=lambda item: (str(item.path), item.line))
            if definition.path == path and definition.identifier.startswith("REQ-")
        )
        return normalize_projection("\n".join(parts))
    path = root / "requirements.md"
    content = strip_fenced_code(files.get(path, ""))
    return normalize_projection(
        without_fields(
            content,
            {"Requirements status", "Confirmed by", "Confirmed at", "Confirmed revision"},
        )
    )


def decision_projection(definition: Definition) -> str:
    return normalize_projection(
        without_fields(
            definition.block,
            {"Status", "Confirmed by", "Confirmed at", "Confirmed revision"},
        )
    )


def significant_decision_projection(definitions: dict[str, Definition]) -> str:
    parts = [
        decision_projection(definition)
        for identifier, definition in sorted(definitions.items())
        if identifier.startswith("DEC-") and definition.fields.get("Significant option", "yes").lower() == "yes"
    ]
    return normalize_projection("\n".join(parts))


def specification_projection(root: Path, files: dict[Path, str]) -> str:
    content = strip_fenced_code(files.get(root / "spec.md", ""))
    return normalize_projection(
        without_fields(
            content,
            {
                "Spec status",
                "Requirements revision",
                "Technical options status",
                "Options confirmed by",
                "Options confirmed at",
                "Options confirmed revision",
                "Status",
                "Confirmed by",
                "Confirmed at",
                "Confirmed revision",
            },
        )
    )


def milestone_plan_projection(root: Path, profile: str, path: Path, content: str) -> str:
    active = strip_fenced_code(content)
    if profile == "lite":
        active = level_two_section(active, "Milestone M1")
    active = without_fields(
        active,
        {
            "Plan status",
            "Spec revision",
            "Base revision",
            "Candidate revision",
            "Reviewed revision",
            "Accepted revision",
            "Release revision",
            "Deployed revision",
            "Status",
            "Blocker",
            "Resume condition",
        },
    )
    active = re.sub(r"(?m)^\s*-\s*\[[ xX]\].*(?:\n|\Z)", "", active)
    return normalize_projection(active)


def plan_paths_by_milestone(root: Path, files: dict[Path, str]) -> dict[int, list[Path]]:
    result: dict[int, list[Path]] = {}
    for path in files:
        if path.parent != root / "plans":
            continue
        match = re.fullmatch(r"M([1-9]\d*)-.+\.md", path.name)
        if match:
            result.setdefault(int(match.group(1)), []).append(path)
    for paths in result.values():
        paths.sort()
    return result


def combined_plan_projection(
    root: Path,
    profile: str,
    milestone: int,
    files: dict[Path, str],
) -> str:
    if profile == "lite" and milestone == 1:
        path = root / "change.md"
        return milestone_plan_projection(root, profile, path, files.get(path, ""))
    parts: list[str] = []
    for path in plan_paths_by_milestone(root, files).get(milestone, []):
        parts.append(path.relative_to(root).as_posix())
        parts.append(milestone_plan_projection(root, profile, path, files[path]))
    return normalize_projection("\n".join(parts))


def milestone_candidate_values(
    root: Path,
    profile: str,
    milestone: int,
    files: dict[Path, str],
) -> list[str]:
    if profile == "lite" and milestone == 1:
        return [first_field_values(files.get(root / "change.md", ""), {"Candidate revision"}).get("Candidate revision", "")]
    return [
        first_field_values(files[plan], {"Candidate revision"}).get("Candidate revision", "")
        for plan in plan_paths_by_milestone(root, files).get(milestone, [])
    ]


def expected_review_digest(
    root: Path,
    profile: str,
    path: Path,
    files: dict[Path, str],
    definitions: dict[str, Definition],
) -> str | None:
    requirement_revision = sha256_revision(requirements_projection(root, profile, files, definitions))
    if path.name == "spec-review.md" and profile in {"standard", "high-assurance"}:
        projection = f"requirements {requirement_revision}\nspecification\n{specification_projection(root, files)}"
        return sha256_revision(projection)
    match = re.fullmatch(r"(plan|code)-review-M([1-9]\d*)\.md", path.name)
    if match:
        kind = match.group(1)
        milestone = int(match.group(2))
        plan_projection = combined_plan_projection(root, profile, milestone, files)
        if not plan_projection:
            return None
        parts = [f"requirements {requirement_revision}"]
        if profile in {"standard", "high-assurance"}:
            parts.append(f"specification {sha256_revision(specification_projection(root, files))}")
        parts.append(f"plan\n{plan_projection}")
        if kind == "code":
            candidates = milestone_candidate_values(root, profile, milestone, files)
            parts.append("candidate revisions\n" + "\n".join(candidates))
        return sha256_revision("\n".join(parts))
    return None


def digest_manifest(
    root: Path,
    profile: str,
    files: dict[Path, str],
    definitions: dict[str, Definition],
) -> dict[str, object]:
    requirement_content = requirements_projection(root, profile, files, definitions)
    decisions = {
        identifier: sha256_revision(decision_projection(definition))
        for identifier, definition in sorted(definitions.items())
        if identifier.startswith("DEC-")
    }
    significant = significant_decision_projection(definitions)
    reviews = {
        path.relative_to(root).as_posix(): expected
        for path in sorted(files)
        if path.parent == root / "reviews" and path.name != "acceptance.md"
        if (expected := expected_review_digest(root, profile, path, files, definitions)) is not None
    }
    return {
        "requirements": sha256_revision(requirement_content),
        "decisions": decisions,
        "technical_options": sha256_revision(significant) if significant else None,
        "specification": (
            sha256_revision(specification_projection(root, files))
            if profile in {"standard", "high-assurance"} and root / "spec.md" in files
            else None
        ),
        "reviews": reviews,
    }


def add_issue(issues: list[Issue], level: str, code: str, message: str, path: Path | str | None = None) -> None:
    issues.append(Issue(level, code, message, str(path) if path is not None else None))


def require_file(root: Path, relative: str, files: dict[Path, str], issues: list[Issue]) -> None:
    if root / relative not in files:
        add_issue(issues, "error", "missing-file", f"required file is missing: {relative}", root / relative)


def validate_layout(root: Path, profile: str, files: dict[Path, str], issues: list[Issue]) -> None:
    require_file(root, "workflow-state.md", files, issues)
    require_file(root, "reviews/acceptance.md", files, issues)
    if profile == "lite":
        require_file(root, "change.md", files, issues)
        require_file(root, "reviews/code-review-M1.md", files, issues)
    elif profile in {"standard", "high-assurance"}:
        for relative in (
            "requirements.md",
            "spec.md",
            "plans/M1-plan.md",
            "reviews/spec-review.md",
            "reviews/plan-review-M1.md",
            "reviews/code-review-M1.md",
        ):
            require_file(root, relative, files, issues)
    if profile == "high-assurance":
        require_file(root, "release-plan.md", files, issues)


def validate_workflow_state(
    path: Path, content: str, strict: bool, issues: list[Issue]
) -> tuple[str, str, dict[str, str]]:
    top_fields = {
        "Run ID",
        "Artifact root",
        "Rigor",
        "Rigor rationale",
        "Commit policy",
        "Delivery target",
        "Workflow status",
        "Technical options status",
        "Current milestone",
        "Current task",
        "Base revision",
        "Initial dirty paths",
        "Owned paths",
        "Last checkpoint",
        "Next safe action",
        "Review mode",
    }
    operational_fields = {
        "Initial staged paths",
        "Initial unstaged paths",
        "Initial untracked paths",
        "Current blocker",
        "Same-cause attempts",
        "Last hypothesis/result",
        "Next differentiated action",
        "Exact resume condition",
    }
    fields = authoritative_fields(content, path, top_fields, issues)
    fields.update(authoritative_fields(content, path, operational_fields, issues, top_only=False))
    required = top_fields | {"Initial staged paths", "Current blocker", "Exact resume condition"}
    for field in sorted(required - fields.keys()):
        add_issue(issues, "error", "missing-state-field", f"workflow-state is missing '{field}'", path)

    profile = fields.get("Rigor", "")
    target = fields.get("Delivery target", "")
    if profile not in ALLOWED_PROFILES:
        add_issue(issues, "error", "invalid-profile", f"invalid rigor profile: {profile!r}", path)
    if fields.get("Commit policy") not in ALLOWED_COMMIT_POLICIES:
        add_issue(issues, "error", "invalid-commit-policy", f"invalid commit policy: {fields.get('Commit policy')!r}", path)
    if target not in ALLOWED_DELIVERY_TARGETS:
        add_issue(issues, "error", "invalid-delivery-target", f"invalid delivery target: {target!r}", path)
    options_status = fields.get("Technical options status", "")
    if options_status not in ALLOWED_OPTIONS_STATES:
        add_issue(issues, "error", "invalid-options-state", "invalid technical options status", path)
    if profile == "lite" and options_status != "not-applicable":
        add_issue(issues, "error", "lite-options-state", "Lite requires technical options status not-applicable", path)
    status = fields.get("Workflow status", "")
    if status not in ALLOWED_WORKFLOW_STATES:
        add_issue(issues, "error", "invalid-workflow-state", f"invalid workflow status: {status!r}", path)
    if fields.get("Review mode") not in ALLOWED_REVIEW_MODES:
        add_issue(issues, "error", "invalid-review-mode", f"invalid review mode: {fields.get('Review mode')!r}", path)
    current_blocker = fields.get("Current blocker", "")
    if current_blocker not in ALLOWED_BLOCKERS:
        add_issue(issues, "error", "invalid-workflow-blocker", "workflow blocker must be none, permission, or external", path)
    if status in {"blocked-permission", "blocked-external"}:
        expected_blocker = "permission" if status == "blocked-permission" else "external"
        if current_blocker != expected_blocker or fields.get("Exact resume condition", "none") in {"", "none", "pending"}:
            add_issue(issues, "error", "incomplete-workflow-blocker", "blocked workflow needs a blocker and exact resume condition", path)
    elif current_blocker != "none" or fields.get("Exact resume condition", "none") not in {"", "none"}:
        add_issue(issues, "error", "contradictory-workflow-blocker", "non-blocked workflow cannot retain a blocker/resume condition", path)

    def normalized_paths(value: str, field_name: str) -> set[PurePosixPath]:
        if value in {"", "none"} or value.startswith("["):
            return set()
        result: set[PurePosixPath] = set()
        for raw in value.split(","):
            item = raw.strip().strip("`").replace("\\", "/")
            if not item:
                continue
            candidate = PurePosixPath(item)
            if candidate.is_absolute() or ".." in candidate.parts:
                add_issue(issues, "error", "unsafe-owned-path", f"{field_name} contains a non-project-relative path", path)
                continue
            parts = tuple(part for part in candidate.parts if part not in {"", "."})
            if parts:
                result.add(PurePosixPath(*parts))
        return result

    def paths_overlap(left: PurePosixPath, right: PurePosixPath) -> bool:
        left_parts = left.parts
        right_parts = right.parts
        return left_parts == right_parts[: len(left_parts)] or right_parts == left_parts[: len(right_parts)]

    if fields.get("Commit policy") in {"auto", "checkpoint"}:
        if fields.get("Initial staged paths", "none") not in {"", "none"}:
            add_issue(
                issues,
                "error",
                "preexisting-index",
                "automatic/checkpoint commits are unsafe while the initial index contains staged content",
                path,
            )
        dirty = normalized_paths(fields.get("Initial dirty paths", ""), "Initial dirty paths")
        owned = normalized_paths(fields.get("Owned paths", ""), "Owned paths")
        overlap = {
            f"{left.as_posix()} <-> {right.as_posix()}"
            for left in dirty
            for right in owned
            if paths_overlap(left, right)
        }
        if overlap:
            add_issue(
                issues,
                "error",
                "dirty-owned-overlap",
                f"automatic/checkpoint commits cannot own initially dirty paths: {', '.join(sorted(overlap))}",
                path,
            )
    if strict and fields.get("Workflow status") != target:
        add_issue(
            issues,
            "error",
            "target-not-achieved",
            f"workflow status {fields.get('Workflow status')!r} does not equal delivery target {target!r}",
            path,
        )
    if strict and not BASE_REVISION_PATTERN.match(fields.get("Base revision", "")):
        add_issue(issues, "error", "invalid-base-revision", "strict validation requires an exact Git/non-Git base revision", path)
    return profile, target, fields


def validate_state_reconciliation(
    state_path: Path,
    state_fields: dict[str, str],
    definitions: dict[str, Definition],
    strict: bool,
    issues: list[Issue],
) -> None:
    current = state_fields.get("Current task", "none")
    if current != "none":
        definition = definitions.get(current)
        if definition is None or not current.startswith("TASK-"):
            add_issue(issues, "error", "invalid-current-task", f"current task is not defined: {current}", state_path)
        elif definition.fields.get("Status") == "completed":
            add_issue(issues, "error", "completed-current-task", f"completed task remains current: {current}", state_path)
    if strict and current != "none":
        add_issue(issues, "error", "active-task-at-delivery", f"strict delivery still has current task: {current}", state_path)


def validate_confirmations(
    root: Path,
    profile: str,
    state_fields: dict[str, str],
    files: dict[Path, str],
    definitions: dict[str, Definition],
    strict: bool,
    issues: list[Issue],
) -> None:
    contract = root / ("change.md" if profile == "lite" else "requirements.md")
    content = files.get(contract)
    if content is None:
        return
    confirmation_names = {
        "Requirements status",
        "Confirmed by",
        "Confirmed at",
        "Confirmed revision",
    }
    if profile == "lite":
        confirmation_names.add("Technical options status")
    fields = authoritative_fields(content, contract, confirmation_names, issues)
    status = fields.get("Requirements status", "")
    confirmation_values = [fields.get(field, "") for field in ("Confirmed by", "Confirmed at", "Confirmed revision")]
    if status not in {"draft", "awaiting-confirmation", "confirmed"}:
        add_issue(issues, "error", "invalid-confirmation-state", f"invalid requirements status: {status!r}", contract)
    if status in {"draft", "awaiting-confirmation"} and any(value not in {"", "none"} for value in confirmation_values):
        add_issue(issues, "error", "premature-confirmation", "unconfirmed requirements contain confirmation metadata", contract)
    if status == "confirmed":
        for field, value in zip(("Confirmed by", "Confirmed at", "Confirmed revision"), confirmation_values):
            if value in {"", "none", "pending"}:
                add_issue(issues, "error", "missing-confirmation", f"missing requirements confirmation field: {field}", contract)
        confirmed_at = fields.get("Confirmed at", "")
        if confirmed_at not in {"", "none", "pending"} and not ISO_TIME_PATTERN.match(confirmed_at):
            add_issue(issues, "error", "invalid-confirmation-time", f"invalid ISO-8601 confirmation time: {confirmed_at}", contract)
        revision = fields.get("Confirmed revision", "")
        if revision not in {"", "none", "pending"} and not REVISION_PATTERN.match(revision):
            add_issue(issues, "error", "invalid-confirmation-revision", "requirements confirmation needs a Git SHA or SHA-256 digest", contract)
        expected_revision = sha256_revision(requirements_projection(root, profile, files, definitions))
        if revision != expected_revision:
            add_issue(
                issues,
                "error",
                "requirements-digest-mismatch",
                "requirements confirmation revision does not match the canonical requirements payload",
                contract,
            )
    if strict and status != "confirmed":
        add_issue(issues, "error", "requirements-unconfirmed", "requirements are not confirmed", contract)
    if strict and profile == "lite" and not level_two_section(strip_fenced_code(content), "Goal and Non-Goals"):
        add_issue(issues, "error", "missing-lite-requirements-scope", "Lite requires the Goal and Non-Goals section", contract)

    significant_decisions: list[Definition] = []
    for identifier, definition in definitions.items():
        if not identifier.startswith("DEC-"):
            continue
        significant = definition.fields.get("Significant option", "yes").lower()
        decision_status = definition.fields.get("Status", "")
        if significant not in {"yes", "no"}:
            add_issue(issues, "error", "invalid-decision-significance", f"{identifier} has invalid Significant option value", definition.path)
        if significant == "yes":
            significant_decisions.append(definition)
        if decision_status not in {"draft", "awaiting-confirmation", "confirmed", "recorded", "not-applicable"}:
            add_issue(issues, "error", "invalid-decision-state", f"{identifier} has invalid status {decision_status!r}", definition.path)
        values = [definition.fields.get(field, "") for field in ("Confirmed by", "Confirmed at", "Confirmed revision")]
        if significant == "yes" and decision_status in {"draft", "awaiting-confirmation"}:
            if any(value not in {"", "none"} for value in values):
                add_issue(issues, "error", "premature-confirmation", f"{identifier} contains confirmation metadata before confirmation", definition.path)
        if strict and significant == "yes" and decision_status != "confirmed":
            add_issue(issues, "error", "decision-unconfirmed", f"{identifier} is not confirmed", definition.path)
        if strict and significant == "no" and decision_status in {"draft", "awaiting-confirmation"}:
            add_issue(issues, "error", "decision-unresolved", f"{identifier} is not recorded", definition.path)
        if significant == "yes" and decision_status == "confirmed":
            for field in (
                "Requirements/risks",
                "Chosen option",
                "Evidence/spikes",
                "Benefits and costs",
                "Operational/migration/lock-in consequences",
                "Rejected alternatives and reasons",
            ):
                if strict and definition.fields.get(field, "").lower() in {"", "pending"}:
                    add_issue(issues, "error", "incomplete-significant-decision", f"{identifier} is missing {field}", definition.path)
            if any(value in {"", "none", "pending"} for value in values):
                add_issue(issues, "error", "missing-confirmation", f"{identifier} is missing confirmation metadata", definition.path)
            if values[1] not in {"", "none", "pending"} and not ISO_TIME_PATTERN.match(values[1]):
                add_issue(issues, "error", "invalid-confirmation-time", f"{identifier} has invalid confirmation time", definition.path)
            if values[2] not in {"", "none", "pending"} and not REVISION_PATTERN.match(values[2]):
                add_issue(issues, "error", "invalid-confirmation-revision", f"{identifier} has invalid confirmation revision", definition.path)
            expected_decision_revision = sha256_revision(decision_projection(definition))
            if values[2] != expected_decision_revision:
                add_issue(
                    issues,
                    "error",
                    "decision-digest-mismatch",
                    f"{identifier} confirmation revision does not match its canonical decision payload",
                    definition.path,
                )

    spec_fields: dict[str, str] = {}
    if profile == "lite":
        options_status = fields.get("Technical options status", "")
    else:
        spec_path = root / "spec.md"
        spec_content = files.get(spec_path, "")
        spec_fields = authoritative_fields(
            spec_content,
            spec_path,
            {
                "Spec status",
                "Requirements revision",
                "Technical options status",
                "Options confirmed by",
                "Options confirmed at",
                "Options confirmed revision",
            },
            issues,
        )
        options_status = spec_fields.get("Technical options status", "")
        spec_status = spec_fields.get("Spec status", "")
        if spec_status not in {"draft", "awaiting-review", "reviewed", "stale"}:
            add_issue(issues, "error", "invalid-spec-state", "specification has an invalid status", spec_path)
        if strict and spec_status != "reviewed":
            add_issue(issues, "error", "spec-not-reviewed", "strict delivery requires Spec status reviewed", spec_path)
        if strict and spec_fields.get("Requirements revision") != fields.get("Confirmed revision"):
            add_issue(
                issues,
                "error",
                "spec-requirements-mismatch",
                "specification does not bind the confirmed requirements payload",
                spec_path,
            )
    if options_status not in ALLOWED_OPTIONS_STATES:
        add_issue(issues, "error", "invalid-options-state", "contract has invalid technical options status", contract)
    if options_status != state_fields.get("Technical options status"):
        add_issue(issues, "error", "options-state-mismatch", "contract and workflow technical options states differ", contract)
    if strict:
        expected_options_status = "confirmed" if significant_decisions else "not-applicable"
        if options_status != expected_options_status:
            add_issue(
                issues,
                "error",
                "options-gate-incomplete",
                f"technical options status must be {expected_options_status}",
                contract,
            )
    if profile != "lite":
        option_values = [
            spec_fields.get(field, "")
            for field in ("Options confirmed by", "Options confirmed at", "Options confirmed revision")
        ]
        spec_path = root / "spec.md"
        if significant_decisions and options_status == "confirmed":
            if any(value in {"", "none", "pending"} for value in option_values):
                add_issue(issues, "error", "missing-options-confirmation", "significant options need aggregate confirmation metadata", spec_path)
            if option_values[1] not in {"", "none", "pending"} and not ISO_TIME_PATTERN.match(option_values[1]):
                add_issue(issues, "error", "invalid-confirmation-time", "technical options confirmation time is invalid", spec_path)
            expected_options_revision = sha256_revision(significant_decision_projection(definitions))
            if option_values[2] != expected_options_revision:
                add_issue(
                    issues,
                    "error",
                    "options-digest-mismatch",
                    "technical options confirmation revision does not match the canonical significant-decision payloads",
                    spec_path,
                )
        elif not significant_decisions and any(value not in {"", "none"} for value in option_values):
            add_issue(issues, "error", "premature-confirmation", "not-applicable technical options contain confirmation metadata", spec_path)


def validate_references(
    files: dict[Path, str], definitions: dict[str, Definition], strict: bool, issues: list[Issue]
) -> None:
    known = set(definitions)
    for path, content in files.items():
        for reference in sorted(ids(strip_fenced_code(content)) - known):
            add_issue(issues, "error", "undefined-id", f"reference has no definition: {reference}", path)

    requirements = {key for key in known if key.startswith("REQ-")}
    acceptances = {key for key in known if key.startswith("AC-")}
    tasks = {key for key in known if key.startswith("TASK-")}
    linked_requirements: set[str] = set()

    if strict:
        for identifier in sorted(requirements):
            statement = definitions[identifier].fields.get("Statement", "")
            if statement.lower() in {"", "pending", "unknown"}:
                add_issue(issues, "error", "incomplete-requirement", f"{identifier} needs a concrete Statement", definitions[identifier].path)

    for identifier in sorted(acceptances):
        definition = definitions[identifier]
        linked = {item for item in ids(definition.fields.get("Requirements", "")) if item.startswith("REQ-")}
        linked_requirements.update(linked)
        if not linked:
            add_issue(issues, "error", "ac-without-requirement", f"{identifier} does not link a requirement", definition.path)
        for reference in sorted(linked - requirements):
            add_issue(issues, "error", "ac-bad-requirement", f"{identifier} links undefined {reference}", definition.path)
        classes = verification_classes(definition.fields.get("Verification class", ""))
        if not classes or not classes <= ALLOWED_VERIFICATION_CLASSES:
            add_issue(issues, "error", "invalid-verification-class", f"{identifier} has invalid/missing verification class", definition.path)
        elif strict and "pending" in classes:
            add_issue(issues, "error", "pending-verification-class", f"{identifier} still has pending verification class", definition.path)
        if strict:
            for field in ("Method", "Passing condition"):
                if definition.fields.get(field, "").lower() in {"", "pending", "unknown"}:
                    add_issue(issues, "error", "incomplete-acceptance", f"{identifier} needs a concrete {field}", definition.path)

    if strict:
        for identifier in sorted(requirements - linked_requirements):
            add_issue(issues, "error", "requirement-without-ac", f"{identifier} is not covered by any acceptance criterion", definitions[identifier].path)

    for identifier in sorted(tasks):
        definition = definitions[identifier]
        linked = {item for item in ids(definition.fields.get("Acceptance", "")) if item.startswith("AC-")}
        if not linked:
            add_issue(issues, "error", "task-without-ac", f"{identifier} does not link acceptance criteria", definition.path)
        for reference in sorted(linked - acceptances):
            add_issue(issues, "error", "task-bad-ac", f"{identifier} links undefined {reference}", definition.path)
        state = definition.fields.get("Status", "")
        if state not in ALLOWED_TASK_STATES:
            add_issue(issues, "error", "invalid-task-state", f"{identifier} has invalid state {state!r}", definition.path)
        classes = verification_classes(definition.fields.get("Verification class", ""))
        if not classes or not classes <= ALLOWED_VERIFICATION_CLASSES:
            add_issue(issues, "error", "invalid-verification-class", f"{identifier} has invalid/missing verification class", definition.path)
        elif strict and "pending" in classes:
            add_issue(issues, "error", "pending-verification-class", f"{identifier} still has pending verification class", definition.path)
        blocker = definition.fields.get("Blocker", "none")
        resume = definition.fields.get("Resume condition", "none")
        if blocker not in ALLOWED_BLOCKERS:
            add_issue(issues, "error", "invalid-task-blocker", f"{identifier} blocker must be none, permission, or external", definition.path)
        if state in {"blocked-permission", "blocked-external"}:
            expected_blocker = "permission" if state == "blocked-permission" else "external"
            if blocker != expected_blocker or resume in {"", "none", "pending"}:
                add_issue(issues, "error", "incomplete-blocker", f"{identifier} needs blocker and exact resume condition", definition.path)
        elif blocker != "none" or resume not in {"", "none"}:
            add_issue(issues, "error", "contradictory-task-blocker", f"{identifier} is not blocked but retains blocker state", definition.path)
        if strict and state != "completed":
            add_issue(issues, "error", "task-not-completed", f"{identifier} is {state!r}, not completed", definition.path)
        if strict:
            for field in ("Dependencies", "Owned paths"):
                if definition.fields.get(field, "").lower() in {"", "pending", "unknown"}:
                    add_issue(issues, "error", "incomplete-task", f"{identifier} needs a concrete {field}", definition.path)


def evidence_is_passing(definition: Definition) -> bool:
    outcome = definition.fields.get("Outcome")
    freshness = definition.fields.get("Freshness")
    return freshness == "current" and outcome == "passed"


def validate_artifacts(root: Path, definition: Definition, strict: bool, issues: list[Issue]) -> None:
    value = definition.fields.get("Artifacts", "")
    if value in {"", "none", "pending"}:
        return
    matches = re.findall(r"`([^`]+)`\s*\(sha256:([0-9a-f]{64})\)", value)
    if not matches:
        add_issue(
            issues,
            "error" if strict else "warning",
            "invalid-artifact-reference",
            f"{definition.identifier} artifacts need initiative-relative paths and SHA-256 digests",
            definition.path,
        )
        return
    for relative, expected_digest in matches:
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            add_issue(issues, "error", "unsafe-artifact-path", f"{definition.identifier} artifact path escapes initiative root", definition.path)
            continue
        artifact = root / candidate
        try:
            artifact.relative_to(root)
            data = safe_read_under_root(root, artifact, binary=True)
            assert isinstance(data, bytes)
        except FileNotFoundError:
            add_issue(issues, "error" if strict else "warning", "missing-artifact", f"{definition.identifier} artifact is missing: {relative}", definition.path)
            continue
        except (OSError, UnicodeError, ValueError):
            add_issue(issues, "error", "unsafe-artifact-path", f"{definition.identifier} artifact path is unsafe or not a regular file", definition.path)
            continue
        actual_digest = hashlib.sha256(data).hexdigest()
        if actual_digest != expected_digest:
            add_issue(issues, "error", "artifact-digest-mismatch", f"{definition.identifier} artifact digest does not match: {relative}", definition.path)


def validate_evidence(
    root: Path, definitions: dict[str, Definition], strict: bool, issues: list[Issue]
) -> dict[str, dict[str, list[Definition]]]:
    by_acceptance: dict[str, list[Definition]] = {}
    by_task: dict[str, list[Definition]] = {}
    for identifier, definition in sorted(definitions.items()):
        if not identifier.startswith("EVID-"):
            continue
        missing = REQUIRED_EVIDENCE_FIELDS - definition.fields.keys()
        for field in sorted(missing):
            add_issue(issues, "error", "missing-evidence-field", f"{identifier} is missing '{field}'", definition.path)

        linked_ac = {item for item in ids(definition.fields.get("Acceptance", "")) if item.startswith("AC-")}
        linked_tasks = {item for item in ids(definition.fields.get("Task", "")) if item.startswith("TASK-")}
        if not linked_ac:
            add_issue(issues, "error", "evidence-without-ac", f"{identifier} does not link acceptance criteria", definition.path)
        if not linked_tasks:
            add_issue(issues, "error", "evidence-without-task", f"{identifier} does not link a task", definition.path)
        elif len(linked_tasks) != 1:
            add_issue(issues, "error", "evidence-multiple-tasks", f"{identifier} must link exactly one task", definition.path)
        for reference in linked_ac:
            by_acceptance.setdefault(reference, []).append(definition)
        for reference in linked_tasks:
            by_task.setdefault(reference, []).append(definition)

        outcome = definition.fields.get("Outcome", "")
        freshness = definition.fields.get("Freshness", "")
        blocker = definition.fields.get("Blocker", "")
        if outcome not in ALLOWED_OUTCOMES:
            add_issue(issues, "error", "invalid-evidence-outcome", f"{identifier} has invalid outcome {outcome!r}", definition.path)
        if freshness not in ALLOWED_FRESHNESS:
            add_issue(issues, "error", "invalid-evidence-freshness", f"{identifier} has invalid freshness {freshness!r}", definition.path)
        if blocker not in ALLOWED_BLOCKERS:
            add_issue(issues, "error", "invalid-evidence-blocker", f"{identifier} has invalid blocker {blocker!r}", definition.path)
        if blocker != "none" and outcome not in {"not-run", "inconclusive"}:
            add_issue(issues, "error", "inconsistent-evidence", f"{identifier} blocker is incompatible with outcome {outcome!r}", definition.path)
        if outcome in {"passed", "failed", "not-applicable", "accepted-risk"} and blocker != "none":
            add_issue(issues, "error", "inconsistent-evidence", f"{identifier} completed outcome cannot retain a blocker", definition.path)
        if outcome == "not-applicable" and definition.fields.get("Actual", "").lower() in {"", "none", "pending", "n/a"}:
            add_issue(issues, "error", "missing-na-reason", f"{identifier} needs a concrete not-applicable reason", definition.path)
        if outcome == "accepted-risk" and definition.fields.get("Authorization", "").lower() in {"", "none", "pending", "not-applicable"}:
            add_issue(issues, "error", "missing-risk-authorization", f"{identifier} accepted risk needs explicit authorization", definition.path)
        if outcome == "accepted-risk":
            for field in ("Risk scope", "Risk impact", "Risk owner", "Risk expiry/revisit"):
                if definition.fields.get(field, "").lower() in {"", "none", "pending", "not-applicable", "n/a"}:
                    add_issue(issues, "error", "incomplete-accepted-risk", f"{identifier} accepted risk is missing {field}", definition.path)

        classes = verification_classes(definition.fields.get("Verification class", ""))
        if not classes or not classes <= ALLOWED_VERIFICATION_CLASSES:
            add_issue(issues, "error", "invalid-verification-class", f"{identifier} has invalid/missing verification class", definition.path)
        elif strict and "pending" in classes:
            add_issue(issues, "error", "pending-verification-class", f"{identifier} still has pending verification class", definition.path)

        if len(linked_tasks) == 1:
            task_id = next(iter(linked_tasks))
            task = definitions.get(task_id)
            if task is not None:
                owned_ac = {item for item in ids(task.fields.get("Acceptance", "")) if item.startswith("AC-")}
                if not linked_ac <= owned_ac:
                    add_issue(issues, "error", "evidence-outside-task", f"{identifier} links AC not owned by {task_id}", definition.path)

        validate_artifacts(root, definition, strict, issues)

        if strict:
            if freshness == "current" and outcome not in {"passed", "not-applicable"}:
                add_issue(issues, "error", "current-evidence-not-passing", f"{identifier} is current/{outcome}", definition.path)
            revision = definition.fields.get("Subject revision", "")
            if not REVISION_PATTERN.match(revision):
                add_issue(issues, "error", "invalid-subject-revision", f"{identifier} needs a Git SHA or SHA-256 subject revision", definition.path)
            candidate_mapping = definition.fields.get("Candidate mapping", "")
            if not REVISION_PATTERN.match(candidate_mapping):
                add_issue(issues, "error", "invalid-candidate-mapping", f"{identifier} needs an exact candidate mapping revision", definition.path)
            recorded_at = definition.fields.get("Recorded at", "")
            if not ISO_TIME_PATTERN.match(recorded_at):
                add_issue(issues, "error", "invalid-evidence-time", f"{identifier} needs an ISO-8601 timestamp", definition.path)
            for field in ("Environment", "Method", "Exit code", "Expected", "Actual", "Sanitization", "Cleanup", "Invalidation"):
                if definition.fields.get(field, "").lower() in {"", "pending", "unknown"}:
                    add_issue(issues, "error", "incomplete-evidence-field", f"{identifier} needs a concrete {field}", definition.path)
            exit_code = definition.fields.get("Exit code", "")
            if exit_code not in {"", "pending", "unknown", "not-applicable"} and not re.fullmatch(r"-?\d+", exit_code):
                add_issue(issues, "error", "invalid-exit-code", f"{identifier} exit code must be an integer or not-applicable", definition.path)
    return {"ac": by_acceptance, "task": by_task}


def validate_coverage(
    definitions: dict[str, Definition], evidence_map: dict[str, dict[str, list[Definition]]], strict: bool, issues: list[Issue]
) -> None:
    if strict:
        groups = {
            "REQ": [item for item in definitions if item.startswith("REQ-")],
            "AC": [item for item in definitions if item.startswith("AC-")],
            "TASK": [item for item in definitions if item.startswith("TASK-")],
            "EVID": [item for item in definitions if item.startswith("EVID-")],
        }
        for kind, identifiers in groups.items():
            if not identifiers:
                add_issue(issues, "error", "empty-traceability", f"strict delivery requires at least one {kind} definition")
        passing_evidence = [
            definition
            for identifier, definition in definitions.items()
            if identifier.startswith("EVID-") and evidence_is_passing(definition)
        ]
        if not passing_evidence:
            add_issue(issues, "error", "empty-traceability", "strict delivery requires current passing evidence")
        complete_chain = False
        for evidence in passing_evidence:
            for task_id in ids(evidence.fields.get("Task", "")):
                task = definitions.get(task_id)
                if task is None or not task_id.startswith("TASK-"):
                    continue
                evidence_acceptance = {
                    item for item in ids(evidence.fields.get("Acceptance", "")) if item.startswith("AC-")
                }
                task_acceptance = {
                    item for item in ids(task.fields.get("Acceptance", "")) if item.startswith("AC-")
                }
                for acceptance_id in evidence_acceptance & task_acceptance:
                    acceptance = definitions.get(acceptance_id)
                    if acceptance and any(
                        requirement.startswith("REQ-") and requirement in definitions
                        for requirement in ids(acceptance.fields.get("Requirements", ""))
                    ):
                        complete_chain = True
                        break
        if not complete_chain:
            add_issue(
                issues,
                "error",
                "empty-traceability",
                "strict delivery requires a complete REQ -> AC -> TASK -> current passing EVID chain",
            )

    for identifier, definition in definitions.items():
        if identifier.startswith("AC-"):
            records = evidence_map["ac"].get(identifier, [])
            passing = [record for record in records if evidence_is_passing(record)]
            if strict and not passing:
                add_issue(issues, "error", "ac-without-evidence", f"{identifier} has no current passing evidence", definition.path)
            if strict and passing:
                required = verification_classes(definition.fields.get("Verification class", "")) - {"pending"}
                covered = set().union(*(verification_classes(record.fields.get("Verification class", "")) for record in passing))
                if not required <= covered:
                    add_issue(issues, "error", "missing-evidence-class", f"{identifier} lacks passing evidence classes: {', '.join(sorted(required - covered))}", definition.path)
        if identifier.startswith("TASK-"):
            records = evidence_map["task"].get(identifier, [])
            passing = [record for record in records if evidence_is_passing(record)]
            state = definition.fields.get("Status")
            if (strict or state == "completed") and not passing:
                add_issue(issues, "error", "task-without-evidence", f"{identifier} has no current passing evidence", definition.path)
            if state == "completed" and any(
                record.fields.get("Freshness") == "current"
                and record.fields.get("Outcome") in {"failed", "inconclusive", "not-run", "accepted-risk"}
                for record in records
            ):
                add_issue(issues, "error", "completed-task-contradicted", f"{identifier} has current non-passing evidence and must reopen", definition.path)
            if (strict or state == "completed") and passing:
                required = verification_classes(definition.fields.get("Verification class", "")) - {"pending"}
                covered = set().union(*(verification_classes(record.fields.get("Verification class", "")) for record in passing))
                if not required <= covered:
                    add_issue(issues, "error", "missing-evidence-class", f"{identifier} lacks passing evidence classes: {', '.join(sorted(required - covered))}", definition.path)


def task_milestones(definitions: dict[str, Definition]) -> dict[int, list[Definition]]:
    result: dict[int, list[Definition]] = {}
    for identifier, definition in definitions.items():
        match = re.fullmatch(r"TASK-M([1-9]\d*)-\d{3}", identifier)
        if match:
            result.setdefault(int(match.group(1)), []).append(definition)
    return result


def validate_milestones(
    root: Path,
    profile: str,
    state_fields: dict[str, str],
    files: dict[Path, str],
    definitions: dict[str, Definition],
    strict: bool,
    issues: list[Issue],
) -> None:
    milestones = task_milestones(definitions)
    plan_groups = plan_paths_by_milestone(root, files)
    if profile in {"standard", "high-assurance"}:
        expected_spec_revision = sha256_revision(specification_projection(root, files))
        plan_field_names = {
            "Plan status",
            "Spec revision",
            "Base revision",
            "Candidate revision",
            "Reviewed revision",
            "Accepted revision",
            "Release revision",
            "Deployed revision",
            "Pinning method",
        }
        for number, plan_paths in sorted(plan_groups.items()):
            for plan_path in plan_paths:
                plan_fields = authoritative_fields(files[plan_path], plan_path, plan_field_names, issues)
                plan_status = plan_fields.get("Plan status", "")
                if plan_status not in {"draft", "awaiting-review", "reviewed", "accepted", "stale"}:
                    add_issue(issues, "error", "invalid-plan-state", f"milestone M{number} plan has invalid status", plan_path)
                if strict and plan_status != "accepted":
                    add_issue(issues, "error", "plan-not-accepted", f"milestone M{number} plan is not accepted", plan_path)
                if strict and plan_fields.get("Spec revision") != expected_spec_revision:
                    add_issue(issues, "error", "plan-spec-mismatch", f"milestone M{number} plan does not bind the reviewed specification", plan_path)
            if strict and number not in milestones:
                add_issue(issues, "error", "plan-without-task", f"milestone M{number} plan has no task definitions", plan_paths[0])
    for number, tasks in sorted(milestones.items()):
        if profile == "lite":
            if number != 1:
                add_issue(issues, "error", "lite-multiple-milestones", "Lite permits only milestone M1", tasks[0].path)
            for task in tasks:
                if task.path != root / "change.md":
                    add_issue(issues, "error", "task-plan-mismatch", f"{task.identifier} must be defined in change.md", task.path)
            require_file(root, "reviews/code-review-M1.md", files, issues)
            continue

        expected_prefix = f"M{number}-"
        for task in tasks:
            relative = task.path.relative_to(root)
            if relative.parent != Path("plans") or not relative.name.startswith(expected_prefix):
                add_issue(
                    issues,
                    "error",
                    "task-plan-mismatch",
                    f"{task.identifier} must be defined in plans/{expected_prefix}*.md",
                    task.path,
                )
        plan_files = plan_groups.get(number, [])
        if not plan_files:
            add_issue(issues, "error", "missing-milestone-plan", f"milestone M{number} has no plan", root / "plans")
        require_file(root, f"reviews/plan-review-M{number}.md", files, issues)
        require_file(root, f"reviews/code-review-M{number}.md", files, issues)

    if strict and milestones:
        highest = max(milestones)
        if state_fields.get("Current milestone") != f"M{highest}":
            add_issue(
                issues,
                "error",
                "current-milestone-mismatch",
                f"workflow current milestone must be M{highest}",
                root / "workflow-state.md",
            )


def validate_reviews(
    root: Path,
    profile: str,
    strict: bool,
    files: dict[Path, str],
    definitions: dict[str, Definition],
    issues: list[Issue],
) -> None:
    review_paths = [
        path
        for path in files
        if path.parent.name == "reviews" and path.name != "acceptance.md"
    ]
    for path in review_paths:
        fields = authoritative_fields(
            files[path],
            path,
            {
                "Status",
                "Rigor",
                "Reviewer/context",
                "Isolation method",
                "Reviewed at",
                "Input contract digest",
                "Repository fingerprint before",
                "Repository fingerprint after",
                "Open blocking findings",
                "Open important findings",
                "Supersedes",
                "Superseded by",
            },
            issues,
        )
        status = fields.get("Status", "")
        if fields.get("Rigor") != profile:
            add_issue(issues, "error", "review-profile-mismatch", "review rigor differs from workflow rigor", path)
        if status not in {"draft", "independent-passed", "degraded-reviewed", "blocked", "stale", "superseded"}:
            add_issue(issues, "error", "invalid-review-state", f"invalid review status: {status!r}", path)
        for field in ("Open blocking findings", "Open important findings"):
            value = fields.get(field)
            if value is None or not value.isdigit():
                add_issue(issues, "error", "missing-review-count", f"review needs numeric '{field}'", path)
            elif status in {"independent-passed", "degraded-reviewed"} and value != "0":
                add_issue(issues, "error", "open-review-findings", f"{field} is {value}", path)
        if profile == "high-assurance" and status == "degraded-reviewed":
            add_issue(issues, "error", "degraded-high-assurance-review", "High-assurance does not allow degraded review", path)
        before = fields.get("Repository fingerprint before", "")
        after = fields.get("Repository fingerprint after", "")
        if status in {"independent-passed", "degraded-reviewed"} and before not in {"", "pending", "none"} and after not in {"", "pending", "none"} and before != after:
            add_issue(issues, "error", "review-mutated-inputs", "repository fingerprint changed during review", path)
        if strict:
            allowed = {"independent-passed"} if profile == "high-assurance" else {"independent-passed", "degraded-reviewed"}
            if status not in allowed:
                add_issue(issues, "error", "review-not-passed", f"review status {status!r} is not allowed for {profile}", path)
            for field in ("Repository fingerprint before", "Repository fingerprint after"):
                value = fields.get(field, "")
                if value in {"", "pending", "none"}:
                    add_issue(issues, "error", "missing-review-fingerprint", f"review is missing '{field}'", path)
                elif not REVISION_PATTERN.match(value):
                    add_issue(issues, "error", "invalid-review-fingerprint", f"review has invalid '{field}'", path)
            contract_digest = fields.get("Input contract digest", "")
            if not REVISION_PATTERN.match(contract_digest):
                add_issue(issues, "error", "missing-review-contract-digest", "review needs the frozen normative input digest", path)
            expected_digest = expected_review_digest(root, profile, path, files, definitions)
            if expected_digest is None:
                add_issue(issues, "error", "missing-review-input", "review has no resolvable normative input projection", path)
            elif contract_digest != expected_digest:
                add_issue(issues, "error", "review-contract-digest-mismatch", "review digest does not match the current normative input projection", path)
            code_review = re.fullmatch(r"code-review-M([1-9]\d*)\.md", path.name)
            if code_review:
                milestone = int(code_review.group(1))
                candidates = milestone_candidate_values(root, profile, milestone, files)
                unique_candidates = {value for value in candidates if REVISION_PATTERN.match(value)}
                if not candidates or len(unique_candidates) != 1 or len(unique_candidates) != len(set(candidates)):
                    add_issue(
                        issues,
                        "error",
                        "ambiguous-review-candidate",
                        f"code review M{milestone} needs one exact candidate revision shared by all milestone plans",
                        path,
                    )
                else:
                    candidate = next(iter(unique_candidates))
                    if before != candidate or after != candidate:
                        add_issue(
                            issues,
                            "error",
                            "review-candidate-mismatch",
                            f"code review M{milestone} fingerprints must equal its candidate revision",
                            path,
                        )
            for field in ("Reviewer/context", "Isolation method"):
                if fields.get(field, "") in {"", "pending", "none"}:
                    add_issue(issues, "error", "missing-review-metadata", f"review is missing '{field}'", path)
            if not ISO_TIME_PATTERN.match(fields.get("Reviewed at", "")):
                add_issue(issues, "error", "invalid-review-time", "review needs an ISO-8601 Reviewed at timestamp", path)


def validate_acceptance(
    root: Path, target: str, strict: bool, files: dict[Path, str], issues: list[Issue]
) -> dict[str, str]:
    path = root / "reviews" / "acceptance.md"
    content = files.get(path)
    if content is None:
        return {}
    fields = authoritative_fields(
        content,
        path,
        {
            "Acceptance status",
            "Delivery target",
            "Base revision",
            "Candidate revision",
            "Reviewed revision",
            "Accepted revision",
            "Release revision",
            "Deployed revision",
        },
        issues,
    )
    status = fields.get("Acceptance status", "")
    if status not in {"draft", "accepted", "blocked", "accepted-risk"}:
        add_issue(issues, "error", "invalid-acceptance-status", f"invalid acceptance status: {status!r}", path)
    if fields.get("Delivery target") != target:
        add_issue(issues, "error", "acceptance-target-mismatch", "acceptance delivery target differs from workflow-state", path)
    if not strict:
        return fields
    if status != "accepted":
        add_issue(issues, "error", "acceptance-not-passed", f"acceptance status is {status!r}", path)
    revisions = {
        field: fields.get(field, "")
        for field in ("Base revision", "Candidate revision", "Reviewed revision", "Accepted revision")
    }
    for field, value in revisions.items():
        pattern = BASE_REVISION_PATTERN if field == "Base revision" else REVISION_PATTERN
        if not pattern.match(value):
            add_issue(issues, "error", "invalid-acceptance-revision", f"{field} needs an exact Git/non-Git revision", path)
    candidate = revisions["Candidate revision"]
    if revisions["Reviewed revision"] != candidate:
        add_issue(issues, "error", "unreviewed-candidate", "reviewed revision does not equal candidate revision", path)
    if revisions["Accepted revision"] != candidate:
        add_issue(issues, "error", "unaccepted-candidate", "accepted revision does not equal candidate revision", path)
    if target in {"release-ready", "deployed"}:
        release_revision = fields.get("Release revision", "")
        if release_revision != candidate:
            add_issue(issues, "error", "release-revision-mismatch", "release revision does not equal accepted candidate", path)
    if target == "deployed" and fields.get("Deployed revision", "") != fields.get("Release revision", ""):
        add_issue(issues, "error", "deployed-revision-mismatch", "deployed revision does not equal release revision", path)
    return fields


def validate_release(
    root: Path,
    target: str,
    strict: bool,
    files: dict[Path, str],
    definitions: dict[str, Definition],
    issues: list[Issue],
) -> dict[str, str]:
    path = root / "release-plan.md"
    content = files.get(path)
    fields = (
        authoritative_fields(
            content,
            path,
            {
                "Status",
                "Delivery target",
                "Candidate revision",
                "Release revision",
                "Deployed revision",
                "Release authority",
            },
            issues,
        )
        if content is not None
        else {}
    )
    if content is not None and fields.get("Delivery target") != target:
        add_issue(issues, "error", "release-target-mismatch", "release-plan delivery target differs from workflow-state", path)
    if not strict:
        return fields
    if target == "implemented":
        if content is not None and fields.get("Status") not in {"not-applicable", "deferred"}:
            add_issue(issues, "error", "invalid-implemented-release-state", "implemented target release plan must explicitly be not-applicable or deferred", path)
        return fields
    if content is None:
        add_issue(issues, "error", "missing-release-plan", f"{target} target requires release-plan.md", path)
        return fields
    allowed_status = {"ready", "deployed"} if target == "release-ready" else {"deployed"}
    if fields.get("Status") not in allowed_status:
        add_issue(issues, "error", "release-not-ready", f"release status does not satisfy {target}", path)
    if fields.get("Release revision", "") in {"", "pending", "not-applicable"}:
        add_issue(issues, "error", "missing-release-revision", "release target needs an exact release revision", path)
    if target == "deployed":
        if fields.get("Deployed revision", "") in {"", "pending", "not-applicable"}:
            add_issue(issues, "error", "missing-deployed-revision", "deployed target needs an observed deployed revision", path)
        release_authority = fields.get("Release authority", "")
        if not is_concrete_release_authority(release_authority):
            add_issue(
                issues,
                "error",
                "missing-release-authority",
                "deployed target needs 'principal=<who>; approval=<immutable reference>'",
                path,
            )
        release_evidence = [
            definition
            for identifier, definition in definitions.items()
            if identifier.startswith("EVID-")
            and "release" in verification_classes(definition.fields.get("Verification class", ""))
            and evidence_is_passing(definition)
        ]
        if not release_evidence:
            add_issue(issues, "error", "missing-post-deploy-evidence", "deployed target needs current passing release/smoke evidence", path)
        for evidence in release_evidence:
            if evidence.fields.get("Authorization") != release_authority:
                add_issue(
                    issues,
                    "error",
                    "release-evidence-authorization-mismatch",
                    f"{evidence.identifier} authorization must equal the recorded release authority",
                    evidence.path,
                )

        state_path = root / "workflow-state.md"
        state_content = files.get(state_path, "")
        ledger_headers, ledger_rows = markdown_table(
            state_content,
            "External Operation Ledger",
        )
        required_headers = [
            "Operation ID / idempotency key",
            "Target and intended effect",
            "Subject revision",
            "Pre-state",
            "Rollback/recovery",
            "State",
            "Recovery query",
            "Result evidence",
        ]
        ledger_heading_count = len(
            re.findall(
                r"(?m)^ {0,3}##\s+External Operation Ledger\s*$",
                strip_fenced_code(state_content),
            )
        )
        if ledger_heading_count != 1 or ledger_headers != required_headers:
            add_issue(
                issues,
                "error",
                "missing-external-operation-ledger",
                "deployed target needs the complete external-operation ledger schema",
                state_path,
            )
        else:
            unresolved_states = {"prepared", "unknown", "blocked-permission", "blocked-external"}
            allowed_states = unresolved_states | {"observed", "rolled-back", "cancelled"}
            placeholders = {"", "-", "pending", "unknown", "none", "not-applicable", "n/a"}
            for row in ledger_rows:
                state = row.get("State", "").lower()
                if state not in allowed_states:
                    add_issue(
                        issues,
                        "error",
                        "invalid-external-operation-state",
                        f"external operation {row.get('Operation ID / idempotency key', '')!r} has invalid state {state!r}",
                        state_path,
                    )
                if state in unresolved_states or state.startswith("blocked-"):
                    add_issue(
                        issues,
                        "error",
                        "unresolved-external-operation",
                        f"external operation {row.get('Operation ID / idempotency key', '')!r} remains {state!r}",
                        state_path,
                    )
                required_cells = (
                    "Operation ID / idempotency key",
                    "Target and intended effect",
                    "Subject revision",
                    "Pre-state",
                    "Rollback/recovery",
                    "State",
                    "Recovery query",
                    "Result evidence",
                )
                if (
                    any(row.get(name, "").strip().lower() in placeholders for name in required_cells)
                    or not REVISION_PATTERN.match(row.get("Subject revision", ""))
                ):
                    add_issue(
                        issues,
                        "error",
                        "incomplete-external-operation-row",
                        f"external operation {row.get('Operation ID / idempotency key', '')!r} has placeholder, missing, or invalid cells",
                        state_path,
                    )
            evidence_ids = {evidence.identifier for evidence in release_evidence}
            deployed_revision = fields.get("Deployed revision", "")
            observed = []
            for row in ledger_rows:
                concrete_fields = (
                    "Operation ID / idempotency key",
                    "Target and intended effect",
                    "Pre-state",
                    "Rollback/recovery",
                    "Recovery query",
                )
                if (
                    row.get("State", "").lower() == "observed"
                    and row.get("Subject revision", "") == deployed_revision
                    and all(row.get(name, "").strip().lower() not in placeholders for name in concrete_fields)
                    and ids(row.get("Result evidence", "")) & evidence_ids
                ):
                    observed.append(row)
            if not observed:
                add_issue(
                    issues,
                    "error",
                    "missing-observed-deployment-operation",
                    "deployed target needs an observed ledger row for the deployed revision, with recovery data and passing release evidence",
                    state_path,
                )
    return fields


def validate_revision_consistency(
    root: Path,
    profile: str,
    target: str,
    state_fields: dict[str, str],
    acceptance_fields: dict[str, str],
    release_fields: dict[str, str],
    files: dict[Path, str],
    definitions: dict[str, Definition],
    strict: bool,
    issues: list[Issue],
) -> None:
    if not strict or not acceptance_fields:
        return
    acceptance_path = root / "reviews" / "acceptance.md"
    if state_fields.get("Base revision") != acceptance_fields.get("Base revision"):
        add_issue(issues, "error", "base-revision-mismatch", "workflow and acceptance base revisions differ", acceptance_path)

    revision_names = {
        "Base revision",
        "Candidate revision",
        "Reviewed revision",
        "Accepted revision",
        "Release revision",
        "Deployed revision",
    }
    milestones = task_milestones(definitions)
    if profile == "lite":
        contract_paths = [root / "change.md"]
        for contract_path in contract_paths:
            content = files.get(contract_path)
            if content is None:
                continue
            fields = authoritative_fields(content, contract_path, revision_names, issues)
            for name in sorted(revision_names):
                if fields.get(name) != acceptance_fields.get(name):
                    add_issue(
                        issues,
                        "error",
                        "contract-revision-mismatch",
                        f"{name} differs between the Lite contract and acceptance",
                        contract_path,
                    )
    else:
        contract_paths = []
        plan_groups = plan_paths_by_milestone(root, files)
        if milestones:
            highest = max(milestones)
            expected_numbers = set(range(1, highest + 1))
            if set(plan_groups) != expected_numbers:
                add_issue(
                    issues,
                    "error",
                    "milestone-sequence-gap",
                    "strict delivery requires one contiguous plan sequence from M1 through the final task milestone",
                    root / "plans",
                )
            milestone_fields: dict[int, dict[str, str]] = {}
            for number in sorted(expected_numbers & set(plan_groups)):
                variants = [first_field_values(files[path], revision_names) for path in plan_groups[number]]
                fields = variants[0]
                milestone_fields[number] = fields
                for path, variant in zip(plan_groups[number][1:], variants[1:]):
                    if variant != fields:
                        add_issue(issues, "error", "milestone-revision-disagreement", f"M{number} plan files disagree on revisions", path)
                for name in ("Candidate revision", "Reviewed revision", "Accepted revision"):
                    if not REVISION_PATTERN.match(fields.get(name, "")):
                        add_issue(issues, "error", "invalid-plan-revision", f"M{number} {name} is invalid", plan_groups[number][0])
                if not BASE_REVISION_PATTERN.match(fields.get("Base revision", "")):
                    add_issue(issues, "error", "invalid-plan-revision", f"M{number} Base revision is invalid", plan_groups[number][0])
                if fields.get("Reviewed revision") != fields.get("Candidate revision") or fields.get("Accepted revision") != fields.get("Candidate revision"):
                    add_issue(issues, "error", "unaccepted-milestone-candidate", f"M{number} reviewed/accepted revisions must equal its candidate", plan_groups[number][0])
            if 1 in milestone_fields and milestone_fields[1].get("Base revision") != state_fields.get("Base revision"):
                add_issue(issues, "error", "milestone-base-mismatch", "M1 base does not equal the workflow base", plan_groups[1][0])
            for number in range(2, highest + 1):
                if number in milestone_fields and number - 1 in milestone_fields:
                    if milestone_fields[number].get("Base revision") != milestone_fields[number - 1].get("Accepted revision"):
                        add_issue(
                            issues,
                            "error",
                            "milestone-continuity-mismatch",
                            f"M{number} base does not equal M{number - 1} accepted revision",
                            plan_groups[number][0],
                        )
            if highest in milestone_fields:
                for name in sorted(revision_names - {"Base revision"}):
                    if milestone_fields[highest].get(name) != acceptance_fields.get(name):
                        add_issue(
                            issues,
                            "error",
                            "contract-revision-mismatch",
                            f"{name} differs between final milestone M{highest} and acceptance",
                            plan_groups[highest][0],
                        )

    if release_fields:
        names = ("Candidate revision",) if target == "implemented" else ("Candidate revision", "Release revision", "Deployed revision")
        for name in names:
            if release_fields.get(name) != acceptance_fields.get(name):
                add_issue(
                    issues,
                    "error",
                    "release-revision-mismatch",
                    f"{name} differs between release-plan and acceptance",
                    root / "release-plan.md",
                )

    candidate = acceptance_fields.get("Candidate revision", "")
    for identifier, definition in definitions.items():
        if identifier.startswith("EVID-") and evidence_is_passing(definition):
            if definition.fields.get("Candidate mapping") != candidate:
                add_issue(
                    issues,
                    "error",
                    "evidence-candidate-mismatch",
                    f"{identifier} is not mapped to the accepted candidate revision",
                    definition.path,
                )

    if target == "deployed":
        deployed = acceptance_fields.get("Deployed revision", "")
        for identifier, definition in definitions.items():
            if (
                identifier.startswith("EVID-")
                and "release" in verification_classes(definition.fields.get("Verification class", ""))
                and evidence_is_passing(definition)
                and definition.fields.get("Subject revision") != deployed
            ):
                add_issue(
                    issues,
                    "error",
                    "deployment-evidence-revision-mismatch",
                    f"{identifier} does not observe the deployed revision",
                    definition.path,
                )


def validate_placeholders(files: dict[Path, str], strict: bool, issues: list[Issue]) -> None:
    for path, content in files.items():
        active_content = strip_fenced_code(content)
        if "{{" in active_content or "}}" in active_content:
            add_issue(issues, "error", "unresolved-template-token", "unresolved template token", path)
        if TEMPLATE_CUE_PATTERN.search(active_content) or BRACKET_PLACEHOLDER_PATTERN.search(active_content) or "TODO(SDD)" in active_content:
            add_issue(
                issues,
                "error" if strict else "warning",
                "template-placeholder",
                "instructional template placeholder remains",
                path,
            )
        if strict and re.search(r"(?mi)^ {0,3}- [^\n:]+:\s*(?:pending|unknown)\s*$", active_content):
            add_issue(issues, "error", "pending-field", "pending/unknown field remains in strict mode", path)
        if strict and re.search(r"(?mi)\|\s*(?:pending|unknown)\s*\|", active_content):
            add_issue(issues, "error", "pending-table-cell", "pending/unknown table cell remains in strict mode", path)


def validate_secrets(files: dict[Path, str], issues: list[Issue]) -> None:
    for path, content in files.items():
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                add_issue(issues, "error", "possible-secret", f"possible {label} found; remove and rotate if real", path)


def redact(value: str | None) -> str | None:
    if value is None:
        return None
    redacted = value
    for pattern in SECRET_PATTERNS.values():
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def main() -> int:
    args = parse_args()
    root = args.initiative_root.resolve()
    if not root.is_dir():
        print(f"error: initiative root is not a directory: {redact(str(root))}", file=sys.stderr)
        return 2

    try:
        files = read_markdown(root)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: cannot safely read initiative Markdown: {redact(str(exc))}", file=sys.stderr)
        return 2
    issues: list[Issue] = []
    state_path = root / "workflow-state.md"
    state_content = files.get(state_path)
    if state_content is None:
        add_issue(issues, "error", "missing-file", "workflow-state.md is required", state_path)
        profile, target, state_fields = "", "", {}
    else:
        profile, target, state_fields = validate_workflow_state(state_path, state_content, args.strict, issues)

    active_files = {path: content for path, content in files.items() if not is_archived_review(root, path)}
    definitions, definition_issues = collect_definitions(active_files)
    issues.extend(definition_issues)

    if args.print_digests:
        if profile not in ALLOWED_PROFILES:
            print("error: cannot compute digests without a valid workflow rigor profile", file=sys.stderr)
            return 2
        print(json.dumps(digest_manifest(root, profile, active_files, definitions), indent=2, ensure_ascii=False))
        return 0

    if profile in ALLOWED_PROFILES:
        validate_layout(root, profile, files, issues)
        validate_confirmations(root, profile, state_fields, files, definitions, args.strict, issues)

    if state_content is not None:
        validate_state_reconciliation(state_path, state_fields, definitions, args.strict, issues)
    validate_references(active_files, definitions, args.strict, issues)
    evidence_map = validate_evidence(root, definitions, args.strict, issues)
    validate_coverage(definitions, evidence_map, args.strict, issues)
    if profile in ALLOWED_PROFILES:
        validate_milestones(root, profile, state_fields, files, definitions, args.strict, issues)
        validate_reviews(root, profile, args.strict, files, definitions, issues)
    acceptance_fields: dict[str, str] = {}
    release_fields: dict[str, str] = {}
    if target in ALLOWED_DELIVERY_TARGETS:
        acceptance_fields = validate_acceptance(root, target, args.strict, files, issues)
        release_fields = validate_release(root, target, args.strict, files, definitions, issues)
    if profile in ALLOWED_PROFILES and target in ALLOWED_DELIVERY_TARGETS:
        validate_revision_consistency(
            root,
            profile,
            target,
            state_fields,
            acceptance_fields,
            release_fields,
            files,
            definitions,
            args.strict,
            issues,
        )
    validate_placeholders(active_files, args.strict, issues)
    validate_secrets(files, issues)

    issues = [
        Issue(issue.level, issue.code, redact(issue.message) or "", redact(issue.path))
        for issue in issues
    ]

    issues.sort(key=lambda issue: (issue.level != "error", issue.path or "", issue.code, issue.message))
    error_count = sum(issue.level == "error" for issue in issues)
    warning_count = sum(issue.level == "warning" for issue in issues)

    if args.as_json:
        print(
            json.dumps(
                {
                    "root": redact(str(root)),
                    "strict": args.strict,
                    "errors": error_count,
                    "warnings": warning_count,
                    "issues": [asdict(issue) for issue in issues],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        for issue in issues:
            location = f" [{issue.path}]" if issue.path else ""
            print(f"{issue.level.upper()} {issue.code}: {issue.message}{location}")
        print(f"validation: {error_count} error(s), {warning_count} warning(s)")

    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
