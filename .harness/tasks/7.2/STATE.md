# Harness State

Updated: 2026-07-09

## Current Snapshot

- Project: k8s-deploy-agent
- Runtime: Claude Code
- Stack: Python 3.11+, uv, pytest
- Current focus: Task 7.2 — anonymous clone 인증 실패 시 안내 문구 추가
- Task source of truth: `tasks/index.json`

## Active Task

| Task | Status | Notes |
|------|--------|-------|
| 7.2 | done | source_repo.py clone_source_repository — anonymous(askpass 없음) 실패에만 안내 문구 덧붙임. RUN_REPORT.md 참고 |

## Verification Command

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

## Important Constraints

- Preserve air-gapped/on-premise operation.
- Do not introduce external SaaS dependencies.
- Do not place secret values in config, generated files, UI, logs, or tests.
- Existing worktree is dirty; do not revert unrelated user changes.
