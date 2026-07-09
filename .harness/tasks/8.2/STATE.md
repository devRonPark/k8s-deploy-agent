# Harness State

Updated: 2026-07-09 17:16 KST

## Current Snapshot

- Project: k8s-deploy-agent
- Runtime: Codex CLI
- Stack: Python 3.11+, uv, pytest
- Current focus: Task 8.2 evidence 기반 port analyzer 추가
- Task source of truth: `tasks/index.json`

## Active Task

| Task | Status | Notes |
|------|--------|-------|
| 8.2 | done | Added `manifest_plan.py` PortCandidate model and deterministic port candidate collection implementation for Dockerfile, Compose, nginx, package scripts, runtime command, and config files. |

## Gate Notes

- Task-decomposer: passes; one analyzer/model interface, no GitOps rendering or UI/report changes.
- Scope/YAGNI: use Python standard library only; keep parsing deterministic and fixture-based.
- TDD: red confirmed with `tests/test_manifest_plan.py -k port` failing on missing `k8s_deploy_agent.manifest_plan` before implementation.

## Verification Command

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q tests/test_manifest_plan.py -k port
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

## Important Constraints

- Preserve air-gapped/on-premise operation.
- Do not introduce external SaaS dependencies.
- Do not place secret values in config, generated files, UI, logs, or tests.
- Do not infer framework default ports as manifest-ready values.
- Do not revert unrelated dirty worktree entries.
