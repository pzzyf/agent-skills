---
name: spec-driven-dev
description: "Use for greenfield or well-scoped feature work where the task originated from a product idea or rough ask and would benefit from a disciplined, document-first pipeline: explore → requirements → spec (milestones + decision records) → independent review → per-milestone plans → independent review → chunked TDD implementation → code review → acceptance. Triggers when the user says 按SOP开发, spec驱动, 文档先行, 先写规格再写代码, spec-driven, 从需求开始实现, or describes a new product/feature and expects a structured handoff from Idea to delivery rather than jumping straight into code."
---

# Spec-Driven Development

A document-first delivery SOP that takes a product idea to a shipped feature through four artifact families (`requirements` → `spec` → `plans` → `reviews`) and a chunked TDD implementation. Every architectural or behavioral change is forced back through the spec, so the docs and the code never drift.

## When to Use

Trigger this skill when the user wants a rigorous, document-first pipeline for a new product or well-scoped feature. Signals:

- Explicit: "按 SOP 开发", "spec 驱动", "文档先行", "先写规格再写代码", "spec-driven", "从需求开始实现".
- Implicit: user describes a product idea / feature and expects a structured handoff from Idea → delivery instead of jumping straight into code; user references `docs/requirements.md`, `docs/spec.md`, `docs/plans/` or asks to "固化/制定/审查" these.
- A new repo where no `docs/spec.md` exists yet, or an existing feature whose behavior is only described verbally.

Do NOT trigger for one-line fixes, pure refactor, "add a button", research/exploration, or any change too small to justify a spec. The litmus test: if you cannot write a `spec.md` Δ before coding, do not use this skill.

## Pipeline Overview

```
Idea → [explore] → requirements.md → spec.md（决策记录 + 里程碑划分） → [spec review]
      → plans/M1..Mn（每里程碑一份） → [plan review]
      → Chunk 1..N（先测试再实现） → [code review] → acceptance → done
```

Each arrow is a gate. Do not move forward until the prior artifact is committed and (where marked) independently reviewed. When implementation surfaces a spec contradiction, STOP implementation, revise the spec, re-review, then resume — never silently deviate.

Work larger than one deliverable increment MUST be sliced into milestones in the spec first; one giant plan covering everything is invalid.

## Required File Layout

```
AGENTS.md                       项目规则、产品边界、非目标、执行流程
docs/requirements.md            需求说明（产品目标、用户、场景、功能/非功能、非目标、技术风险、成功标准）
docs/spec.md                    产品与技术规格（…、关键决策与理由、里程碑划分、验收标准）
docs/plans/M1-<slug>.md         里程碑 1 实施计划（Chunk → Task → Files/Interfaces/Test cases/Steps，含 DoD）
docs/plans/M2-<slug>.md         里程碑 2 实施计划（按需；单里程碑项目只有 M1）
docs/reviews/spec-review.md     规格独立审查记录
docs/reviews/plan-review-M1.md  计划独立审查记录（每里程碑一份）
docs/reviews/code-review.md     代码独立审查记录（里程碑验收时滚动更新；可选：acceptance.md）
```

If `AGENTS.md` is missing, draft it first: it pins product boundaries, non-goals, tech constraints, and the execution flow itself. All later artifacts inherit its constraints.

## Stage 0 — Explore（发散）

Before writing requirements, explore cheaply. This stage is conversation, not documentation.

- 用提问澄清：真实用户是谁、最痛的场景是哪个、什么算做成。
- 给 2–3 个候选方向，各带一行代价/收益，明确推荐一个并说明理由。
- 识别技术未知：没验证过的库 / API / 兼容性，记录下来带入 Stage 1 的技术风险节。
- Kill bad ideas here — 在此否决一个方向的成本是一句话；到 spec 阶段否决的成本是返工。

Do NOT over-explore: 方向已明确时直接进 Stage 1。Gate: 用户选定方向。

## Stage 1 — Requirements (`docs/requirements.md`)

Capture the idea before designing it. Write, do not bullet-spray.

1. **产品目标** — one or two sentences on what this is and why.
2. **目标用户** — who, and who is explicitly NOT served.
3. **核心使用场景** — numbered, written as user actions in order.
4. **功能需求** — grouped by capability; each item is verifiable.
5. **体验要求** — interaction, responsive, accessibility expectations.
6. **非目标** — explicit anti-scope. This is the most important section for preventing scope creep; write it before any feature list.
7. **技术风险与未知** — 未验证的依赖 / 集成 / 性能假设，每项标注验证方式（spike / 查阅文档 / 原型）。没有也要写"无"。Stage 0 发现的未知必须落在这里。
8. **成功标准** — measurable: usability, resilience, test coverage, build/lint green.

End the file with a status line: `**状态：** 已确认，可进入规格设计`. Confirm with the user before advancing — requirements lock is cheap, spec rework is expensive.

Commit prefix: `docs: 固化 <feature> 需求`.

## Stage 2 — Spec (`docs/spec.md`)

Translate requirements into a buildable contract. The spec is the single source of truth for behavior; code that contradicts the spec is a bug.

Required sections (adapt names to the project):

1. **产品范围** — one paragraph restating scope, including storage/persistence model.
2. **信息架构** — named page regions / modules.
3. **数据模型** — TypeScript interfaces with field-level constraints.
4. **状态与持久化** — component state shape, storage keys, hydration flow, error/fallback behavior.
5. **领域行为** — per-feature rules: creation, editing, completion, deletion, filtering, sorting, statistics. Each rule must be testable as a pure function assertion where possible.
6. **视觉规格** — direction, palette, contrast (WCAG AA), responsive breakpoints, touch targets, reduced-motion.
7. **组件与文件边界** — a file tree with one-line responsibilities; pure logic MUST live outside JSX.
8. **可访问性与响应式** — language, labels, focus, live regions, keyboard, viewport rules.
9. **错误和边界情况** — enumerate each edge case and its required behavior.
10. **关键决策与理由** — one entry per significant technical/architectural choice: what was chosen, why, which alternatives were rejected, why rejected. Decisions must be recorded before code; decisions surfaced during implementation are back-filled here.
11. **里程碑划分** — when the work exceeds one deliverable increment or contains independently verifiable subsystems, slice M1..Mn: each milestone gets a one-line Goal (an independently verifiable increment, e.g. "打通最小链路验证 X 兼容性"), its scope, and its explicit non-scope. Single-milestone projects state "M1 = 全部".
12. **验收标准** — numbered, each mappable to an automated test or manual check.

Hard rules:
- No unbounded behavior. "Fresh data, hydrate from storage, loading→ready gate, don't write empty array before hydration" — say it explicitly.
- Every statistic / filter / sort rule is a named formula, not prose.
- Non-goals from requirements MUST re-appear (or be referenced) so they can't leak in.
- If a behavior can be a pure function, require it to be one, and require a test.
- Every rejected alternative MUST be named in 关键决策与理由 — "为什么不选 X" is as important as "选了什么", so no one re-introduces a rejected approach later.

Commit prefix: `docs: 固化 <feature> 需求与规格` (combine with requirements if staged together).

## Spikes（技术验证）

Technical risks from requirements §7 are resolved by spikes, never by guessing them into the spec:

- A spike is **time-boxed exploration** (default ≤ half a day / ≤ one task). Its output is an answer, not production code.
- Spike tasks in a plan are prefixed `[spike]`; acceptance = a specific question has a definite answer.
- Spike conclusions MUST be back-filled into spec §关键决策与理由. Spike code is thrown away by default; if any of it is genuinely worth keeping, rewrite it through the normal TDD flow.
- High-risk unknowns (core flow depends on an unverified third party) belong in M1's Goal: 先打通最小链路验证可行性，再扩大投资.

## Independent Review Protocol

All independent reviews (spec / plan / code) follow one protocol. "Independent" is a mechanism, not an attitude:

1. **Reviewer is a fresh context.** Dispatch a new subagent (or a new session) to review. The author session MUST NOT review its own work. The reviewer gets read-only tools and MUST NOT modify any file.
2. **Minimal input.** Give the reviewer only upstream artifacts — spec review: `AGENTS.md` + `requirements.md` + `spec.md`; plan review: + the milestone plan; code review: spec + plan + the full diff + test/build output. Do NOT pass the author's reasoning or conversation history: independence comes from information isolation.
3. **Output format.** Findings tiered **阻断 / 重要 / 次要**, each with file/section location and a suggested fix; end with a status line (e.g. `已通过独立审查，可进入实施计划`).
4. **Fix loop.** The author fixes all 阻断 + 重要, commits, and the reviewer (still read-only) re-verifies and closes them. 次要 findings are recorded and may be deferred.

Record reviews under `docs/reviews/`. If the environment truly cannot spawn a separate context, mark the review record with `（降级：同会话审查）` so later readers know the gate was weakened.

## Stage 3 — Plan (`docs/plans/M<n>-<slug>.md`)

One plan per milestone. Decompose the spec into Chunks → Tasks, ordered so each task is independently verifiable and testable. Milestone plans may be refined rolling-wave (M2's plan after M1 lands); inside a milestone, the plan is frozen once reviewed.

Per `plan.md` structure:

- **Goal** + the milestone's verifiable increment, + **Spec 对照** (which spec sections this plan implements).
- **全局约束** (tech stack lock, persistence lock, non-goal lock, test-first lock, stop-on-spec-conflict).
- **Chunk N → Task N.M**, each Task has:
  - **Files:** Create / Modify / Delete (explicit lists).
  - **Interfaces:** TypeScript signatures for new modules (so the spec → code contract is pinned before coding).
  - **Test cases:** enumerated assertions the tests must cover — written before implementation.
  - **Steps:** ordered checkboxes, ending with `npm run <task-test>`, then a Commit step with a prescribed commit message.
- **Definition of Done:** spec acceptance criteria mapped to artifacts; builds/lint/tests green; history layered docs → code.

Hard rules:
- A task with no automated test AND no explicit manual acceptance step is invalid.
- Implementation work precedes cleanup only when the cleanup unblocks tests (e.g., remove starter templates before setting up the test harness).
- Each task's test run is targeted (e.g., `npm run test:unit -- path/to/file.test.ts`), not the full suite, to keep the feedback loop tight.
- Prescribe commit messages per task so history reads as a narrative.
- Spike tasks carry the `[spike]` prefix and a time box.

Commit prefix: `docs: 制定并审查 <feature> M<n> 实施计划`.

### Stage 3b — Plan independent review

Per the Independent Review Protocol, recorded in `docs/reviews/plan-review-M<n>.md`. Verify: test harness won't miscollect unrelated tests; cleanup scope is complete; every spec acceptance criterion in this milestone has an executing task; spikes are time-boxed; deployment/release ordering pins the exact commit. Fix all 阻断 + 重要 before implementing.

## Stage 4 — Implementation (Chunked TDD)

The plan IS the todo list. Work tasks in order. For each task:

1. **Tests first.** Write the failing test cases enumerated in the plan; run and confirm they fail for the right reason.
2. **Minimum implementation** to turn the tests green. No speculative abstraction.
3. **Run the task's targeted test** (not the full suite). Fix until green.
4. **Commit** with the message prescribed in the plan.

Inter-task rules:
- Stop on spec conflict. If a test reveals an under-specified behavior, revise `docs/spec.md`, re-review (or at minimum re-read the review notes), then resume. Never absorb a silent deviation.
- Keep pure domain logic (validation, filtering, sorting, stats) in modules with no React/DOM/IO imports, so they are unit-testable without a jsdom harness.
- Keep interaction + IO (localStorage, effects, hydration, cross-midnight timers) in component layers, tested separately for race conditions and error fallback.
- Hydration / persistence gate: write the failing race-condition test before the gate. The rule "don't overwrite existing data with an empty initial array" is the single most common production bug this SOP prevents.
- New decisions made under pressure (library swap, schema change) are back-filled into spec §关键决策与理由 in the same commit.

Commit prefixes by chunk: `chore:` (cleanup/scaffold), `test:` (test harness), `feat:` (domain/storage/UI), `fix:` (review fixes), `docs:` (reviews/acceptance).

### Execution Protocol

- **The plan is a state machine.** Checkboxes are the single source of truth for progress. Tick each step the moment it completes; never batch-tick afterwards.
- **Resume after interruption.** A new session reads only `AGENTS.md` → `spec.md` → the current milestone plan, and continues from the first unchecked task. Never resume from memory.
- **Execution mode.** Default: the main session works tasks sequentially. When a task touches many modules or large files (context pollution risk), dispatch a fresh subagent per task with that task's full definition; the main session only integrates and ticks. The reviewer is always a separate context (see Independent Review Protocol).

## Stage 5 — Independent code review

Per the Independent Review Protocol: a read-only reviewer audits the full diff from the spec commit to HEAD against `AGENTS.md`, `docs/spec.md`, the milestone plan, and the test/build output. Tiers again **阻断 / 重要 / 次要**. Record in `docs/reviews/code-review.md` (rolling update per milestone). The author fixes all 阻断 + 重要 and adds regression tests; reviewer re-verifies read-only. No blocking items may remain open. If there are no code issues, commit `docs: 记录独立代码审查` — never manufacture a fake `fix:`.

## Stage 6 — Acceptance & delivery

1. Run `npm test`, `npm run lint`, `npm run build` (adapt to the project's real commands — read `package.json` scripts; never assume).
2. Create or update `docs/reviews/acceptance.md` mapping each spec acceptance criterion of this milestone to its automated test / static check / manual evidence.
3. Manual QA only when the user explicitly authorizes (browser interaction, visual QA, multi-viewport checks).
4. Confirm git working tree, spec/plan checkboxes, and review records are mutually consistent.
5. Deploy/release following the plan's prescribed ordering, pinning the exact committed SHA.
6. Multi-milestone projects: repeat Stages 3–6 per milestone; acceptance.md accumulates.

## Workflow at a Glance

| Stage | Artifact | Gate to advance |
|---|---|---|
| 0 Explore | 对话 + 候选方向 | User picks a direction |
| 1 Requirements | `docs/requirements.md` | User confirms; status line set |
| 2 Spec | `docs/spec.md`（决策 + 里程碑） | Spec review passes (阻断+重要 closed) |
| 3 Plan | `docs/plans/M<n>-*.md` | Plan review passes (阻断+重要 closed) |
| 4 Implementation | Chunked TDD commits（checkbox 状态机） | Each task's targeted test green |
| 5 Code review | `docs/reviews/code-review.md` | No open 阻断 / 重要 |
| 6 Acceptance | `docs/reviews/acceptance.md` + green build/lint/test | Delivery pinned to exact SHA |

## Anti-Patterns to Refuse

- Coding before `spec.md` Δ exists for the change.
- Writing a `feat:` task with no test and no manual acceptance step.
- Absorbing a spec violation silently instead of revising the spec.
- Skipping either independent review (spec or plan) before implementing.
- **自己审自己** — the author session acting as its own "independent" reviewer.
- Skipping milestone slicing on large work and writing one giant plan.
- Treating a spike as a deliverable: exploration code merged without being rewritten through TDD.
- Making a technical decision without recording the rejected alternatives.
- Resuming from memory after an interruption instead of re-reading the plan's checkbox state.
- Letting the persistence effect write an empty initial array over existing local data (always gate on `hydrationState: loading → ready`).
- Letting pure domain logic leak into JSX or component files.
- Adding a feature listed in 非目标, even if "easy".
- Manufacturing a `fix:` commit when the review found no code issue.

## Adapting to Non-Greenfield Work

For changes inside an already-spec'd project:
1. Write a `spec.md` Δ (only the affected sections) and a `requirements.md` Δ if user-facing.
2. Re-review only the Δ.
3. Add or update the affected milestone plan; skip already-done tasks. A change introducing a new subsystem gets its own `M<n>` plan.
4. Implement, review, accept as above.

The flow is identical; only the artifact size shrinks to the Δ.
