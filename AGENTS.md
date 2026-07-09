# k8s-deploy-agent — AGENTS.md

Codex entrypoint for this harness template. Codex must operate from the same
project rules, task sources, and verification gates that Claude Code uses.

## Project Overview

`k8s-deploy-agent` automates repetitive Kubernetes migration preparation work
in customer on-premise or air-gapped environments.

The agent analyzes an application source repository and generates initial
review artifacts for running the application on Kubernetes:

- repository analysis report
- Jenkinsfile for Jenkins Kubernetes Plugin based CI
- Kaniko image build/push commands
- Rancher Fleet GitOps manifests
- Kubernetes Namespace, Deployment, Service, and ConfigMap manifests
- dry-run dashboard for operator review
- review-only Dockerfile and `.dockerignore` proposals
- secret redaction checks

Future work may connect this agent to an on-premise LLM running inside the
customer environment. Do not introduce external SaaS calls.

## Runtime

- Primary agent runtime: Codex CLI
- Language: Python 3.11+
- Package manager: uv
- Entry point: `k8s-deploy-agent`
- Default verification: `UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q`

## Read Order

At the start of a session, read these files before planning or editing:

1. `CLAUDE.md`
2. `harness.toml`
3. `tasks/index.json`
4. `Plans.md`
5. `BLUEPRINT.md` when architecture or command provenance matters

On resumed work, follow the recovery order in `CLAUDE.md`:

1. `tasks/index.json` to identify the `wip` or user-specified Task
2. `.harness/tasks/<task-key>/STATE.md`
3. `.harness/tasks/<task-key>/RUN_REPORT.md` if it exists
4. latest entries in `.harness/LESSONS.md`
5. `Plans.md`
6. only the extra files listed in `.harness/CONTEXT_INDEX.md` that are needed

## Source Of Truth

- `CLAUDE.md` is the canonical harness rulebook for planning, implementation,
  testing, review, GitHub flow, and `.harness/` state documents.
- `tasks/index.json` is the task status source of truth.
- `Plans.md` is a generated human-readable snapshot. Do not edit it directly;
  run `python3 scripts/sync_plans.py` after task JSON changes.
- `harness.toml` `[github]`, `[review]`, `[test]`, and `[plan]` sections are
  summary indexes for the `CLAUDE.md` rules, not independently parsed runtime
  configuration.
- `agents/quality-gates.md` is the shared scope, YAGNI, review, and reporting
  gate. Claude Code may get ponytail/caveman as plugin enhancements, but Codex
  must apply the same principles from this repo file directly.

## Project Engineering Rules

- Preserve offline/on-premise operation.
- Do not store secret values in config, generated files, logs, UI, or tests.
- Use credential IDs or environment variable names instead of raw credentials.
- Keep dry-run behavior deterministic and safe.
- Prefer Python standard library unless a dependency clearly earns its cost.
- Keep generated manifests simple and reviewable.
- Keep source repository write-back and GitOps write-back behind explicit validation gates.
- For UI/dashboard changes, also generate dry-run output and inspect `index.html` when practical.

## Codex Compatibility Rules

Claude Code slash commands and plugins may not exist in Codex. When a
`CLAUDE.md` workflow names a slash command, perform the equivalent repository
procedure directly:

| Claude Code workflow | Codex equivalent |
|---|---|
| `/grill-me` | Use `$grill-me` from `.agents/skills/grill-me/SKILL.md` for the interview and PRD procedure. |
| `/harness-plan` | Use `$harness-plan` from `.agents/skills/harness-plan/SKILL.md` to build planning context, produce/validate a proposal, then apply it. |
| `/harness-work` | Use `$harness-work` from `.agents/skills/harness-work/SKILL.md` to select a `todo` task, enforce the task-decomposer gate, implement, verify, and review. |
| `/harness-review` | Use `$harness-review` from `.agents/skills/harness-review/SKILL.md` to review the diff against `CLAUDE.md`, the target task, and acceptance evidence. |
| `/harness-progress` | Use `$harness-progress` from `.agents/skills/harness-progress/SKILL.md` for read-only progress summaries. |
| `/harness-sync` | Use `$harness-sync` from `.agents/skills/harness-sync/SKILL.md` to validate `tasks/index.json` and regenerate `Plans.md`. |
| Harness YAGNI trim | Use `$harness-yagni-trimmer` from `.agents/skills/harness-yagni-trimmer/SKILL.md` to review and reduce harness/template complexity for solo-builder use. |

Do not assume the Claude Code plugin has performed any gate automatically.
Codex must execute the same gates explicitly.

Do not assume ponytail or caveman plugins run in Codex. When a Claude workflow
relies on those plugins for scope control or terse reporting, use
`agents/quality-gates.md` instead.

## Git Workflow Helpers

| Claude Code command | Codex skill |
|---|---|
| `/branch-checkout` | `$branch-checkout` from `.agents/skills/branch-checkout/SKILL.md` |
| `/git-push` | `$git-push` from `.agents/skills/git-push/SKILL.md` |
| `/pr-create` | `$pr-create` from `.agents/skills/pr-create/SKILL.md` |
| `/rescue-from-main` | `$rescue-from-main` from `.agents/skills/rescue-from-main/SKILL.md` |

These helpers must inspect `git status` and the current branch before changing
branches, pushing, or creating PRs. Never force push or discard local changes.

## Mandatory Gates

- Core workflow is `spec -> plan -> isolated work -> TDD -> fresh verification -> review -> finish`.
- Before adding or changing task rows, use the planning proposal contract in
  `CLAUDE.md` and the scripts:
  `build_planning_context.py`, `validate_task_proposal.py`,
  `apply_task_proposal.py`, and `sync_plans.py`.
- Before implementation, confirm the selected task passes
  `agents/task-decomposer.md` granularity criteria and
  `agents/quality-gates.md` scope/YAGNI criteria.
- After implementation and before review, follow `agents/test-agent.md`: run
  the task Acceptance command and the relevant project test suite, and record
  TDD or explicit exception evidence.
- During review, apply `agents/quality-gates.md`: findings first, verification
  evidence first, and only useful residual risk after approval.
- Do not mark a task `done` unless the Acceptance evidence has passed. GitHub
  Actions must not convert task status; the active agent updates
  `tasks/index.json` and regenerates `Plans.md`.

## State Documents

- Root `.harness/STATE.md`, `HANDOFF.md`, `TASKS.md`, `LOG.md`,
  `CHECKPOINTS.md`, and `RUN_REPORT.md` are templates. Do not write live task
  state into them.
- Store live context under `.harness/tasks/<task-key>/` and update that Task's
  `STATE.md` before risky work and after meaningful work units.
- Append errors and fixes to `.harness/tasks/<task-key>/LOG.md`; add durable
  prevention rules to root `.harness/LESSONS.md`.
- Summarize decisions, changed files, verification evidence, and handoff risks
  in `.harness/tasks/<task-key>/RUN_REPORT.md` after meaningful work or before
  handoff.
- Update `.harness/CONTEXT_INDEX.md` when creating a file or changing a file's
  role.

## Response Language

Use Korean for user-facing responses, unless the user requests otherwise.
Keep code, commands, filenames, and proper nouns unchanged.
