# Harness State

Updated: 2026-07-09 16:44 KST

## Current Snapshot

- Project: k8s-deploy-agent
- Runtime: Codex CLI
- Stack: Python 3.11+, uv, pytest
- Current focus: Task 8.1 monorepo workspace service discovery 개선
- Task source of truth: `tasks/index.json`

## Active Task

| Task | Status | Notes |
|------|--------|-------|
| 8.1 | done | Added monorepo fixture test and updated `analyzer.py` to discover common service dirs, `apps/*`, `services/*`, `packages/*`, workspace markers, and ignored directory boundaries. |

## Gate Notes

- Task-decomposer: passes; one observable analyzer discovery outcome, one code surface, Acceptance targets monorepo tests.
- Scope/YAGNI: keep changes in `analyzer.py` and `tests/test_build_profile.py`; no manifest planning or renderer behavior in this Task.
- TDD: red confirmed with `UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q tests/test_build_profile.py -k monorepo` failing because `analysis.service_names == []`.

## Verification Command

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q tests/test_build_profile.py -k monorepo
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

## Important Constraints

- Preserve air-gapped/on-premise operation.
- Do not introduce external SaaS dependencies.
- Do not place secret values in config, generated files, UI, logs, or tests.
- Do not revert unrelated dirty worktree entries.
