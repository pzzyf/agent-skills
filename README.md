# agent-skills

Personal collection of [Agent Skills](https://agentskills.io) for coding agents (opencode, Claude Code, Codex, Cursor, and 70+ more).

## Skills

| Skill | What it does |
|---|---|
| [`spec-driven-dev`](./skills/spec-driven-dev) | Risk-scaled, document-first delivery: preflight → confirmed requirements/options → pre-spec spikes → reviewed spec/plans → task-appropriate verification and correction loops → traceable evidence/reviews → precise implemented, release-ready, or deployed delivery. |
| [`push-reviewed-diff`](./skills/push-reviewed-diff) | After explicit user approval of the current diff, verify the scope, commit the reviewed changes if needed, push the current branch to origin without force, and confirm remote state. |

`spec-driven-dev` provides Lite, Standard, and High-assurance profiles; stack-neutral domain adapters; reusable artifact templates; and scripts that safely scaffold initiatives and validate the `REQ → AC → TASK → EVID` chain, transitive review freshness, milestone revision continuity, and authorized deployment-ledger reconciliation.

## Install

```bash
# Install a single skill globally (recommended)
npx skills add pzzyf/agent-skills --skill spec-driven-dev -g -y

# Install to a specific agent (e.g. opencode)
npx skills add pzzyf/agent-skills --skill spec-driven-dev -g -a opencode -y

# List all skills in this repo without installing
npx skills add pzzyf/agent-skills --list
```

## Layout

```
skills/
└── <skill-name>/
    ├── SKILL.md
    ├── agents/          # Optional agent metadata
    ├── references/      # Detailed contracts and domain adapters
    ├── assets/          # Reusable templates
    ├── scripts/         # Scaffolding and validation helpers
    └── tests/           # Helper regression tests
```

Each skill is a directory with a required `SKILL.md` containing YAML frontmatter (`name`, `description`) and Markdown instructions. Supporting directories are optional. The CLI auto-discovers skills under `skills/`.

## License

MIT
