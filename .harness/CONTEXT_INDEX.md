# Harness Context Index

Use this index to avoid rereading unrelated files.

| Path | Purpose |
|------|---------|
| `AGENTS.md` | Codex CLI project rules and harness workflow |
| `CLAUDE.md` | Canonical harness rulebook shared by Claude Code and Codex procedures |
| `BLUEPRINT.md` | Harness structure index and command mapping |
| `harness.toml` | Project harness metadata, commands, and safety settings |
| `tasks/index.json` | Task status source of truth |
| `Plans.md` | Human-readable snapshot generated from `tasks/index.json` |
| `.harness/STATE.md` | Current session snapshot |
| `.harness/HANDOFF.md` | Resume instructions for the next session |
| `.harness/LOG.md` | Append-only work and error log |
| `.harness/LESSONS.md` | Reusable prevention rules |
| `.harness/RUN_REPORT.md` | Root run-report template for task-specific evidence |
| `.harness/events/planning.jsonl` | Planning proposal event log |
| `.harness/shared/planning/` | Planning context runs, proposed task files, and decomposition reports |
| `.harness/tasks/` | Task-specific live context directories |
| `agents/task-decomposer.md` | Task splitting and planning gate |
| `agents/test-agent.md` | Acceptance and test verification gate |
| `agents/quality-gates.md` | Shared scope, YAGNI, review, and reporting gate |
| `.agents/skills/` | Codex repo-scoped harness workflow skills |
| `.claude/commands/` | Claude Code local command wrappers for harness workflows |
| `scripts/tasklib.py` | Shared JSON-backed task state helpers |
| `scripts/validate_tasks.py` | Validate `tasks/index.json` structure and task rules |
| `scripts/sync_plans.py` | Regenerate `Plans.md` from `tasks/index.json` |
| `scripts/build_planning_context.py` | Create planning proposal context runs |
| `scripts/validate_task_proposal.py` | Validate proposed tasks before apply |
| `scripts/apply_task_proposal.py` | Apply validated task proposals and sync plans |
| `scripts/planning_log.py` | Append human-readable planning events |
| `docs/demo-scenario.md` | Current demo workflow |
| `docs/ui-ux-plan.md` | Future operator console plan |
| `docs/PRD.md` | Operator console MVP product requirements |
| `docs/UserFlow.md` | Operator console screen flow, source input modes, inputs, outputs, and error states |
| `docs/Architecture.md` | Operator console architecture, source input boundaries, and verification strategy |
| `docs/monthly-demo.md` | Team monthly meeting demo runbook |
| `docs/DockerfilePlan.md` | Dockerfile writing practices and deterministic build profile planning |
| `docs/AgentWorkflowOverview.md` | Executive workflow overview for the implemented source-to-Kubernetes preparation flow |
| `pyproject.toml` | Python package and script configuration |
| `analyzer.py` | Repository service discovery and BuildProfile generation |
| `build_profile.py` | Dockerfile proposal pre-analysis BuildProfile data model |
| `dockerfile_gate.py` | Dockerfile proposal confidence and unresolved-question gate |
| `dockerfile_proposal.py` | Review-only Dockerfile proposal renderer |
| `dockerfile_validation.py` | Dockerfile proposal validation report renderer |
| `ui.py` | Static dry-run dashboard renderer |
| `tests/test_cli_dry_run.py` | Main dry-run behavior tests |
| `tests/test_build_profile.py` | BuildProfile analyzer behavior tests |
| `web.py` | Local operator console HTTP server, source input mode handling, and HTML shell |
