# agent-skills

Personal collection of [Agent Skills](https://agentskills.io) for coding agents (opencode, Claude Code, Codex, Cursor, and 70+ more).

## Skills

| Skill | What it does |
|---|---|
| [`spec-driven-dev`](./skills/spec-driven-dev) | Document-first delivery SOP: requirements → spec → review → plan → review → chunked TDD → code review → acceptance. |

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
    └── SKILL.md
```

Each skill is a directory with a `SKILL.md` file containing YAML frontmatter (`name`, `description`) and Markdown instructions. The CLI auto-discovers skills under `skills/`.

## License

MIT