# Harness Context Index

Use this index to avoid rereading unrelated files.

| Path | Purpose |
|------|---------|
| `AGENTS.md` | Codex CLI project rules and harness workflow |
| `harness.toml` | Project harness metadata, commands, and safety settings |
| `Plans.md` | Task status source of truth |
| `.harness/STATE.md` | Current session snapshot |
| `.harness/HANDOFF.md` | Resume instructions for the next session |
| `.harness/LOG.md` | Append-only work and error log |
| `.harness/LESSONS.md` | Reusable prevention rules |
| `agents/task-decomposer.md` | Task splitting and planning gate |
| `agents/test-agent.md` | Acceptance and test verification gate |
| `docs/demo-scenario.md` | Current demo workflow |
| `docs/ui-ux-plan.md` | Future operator console plan |
| `docs/PRD.md` | Operator console MVP product requirements |
| `docs/UserFlow.md` | Operator console screen flow, inputs, outputs, and error states |
| `docs/Architecture.md` | Operator console architecture, boundaries, and verification strategy |
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
| `web.py` | Local operator console HTTP server and HTML shell |
