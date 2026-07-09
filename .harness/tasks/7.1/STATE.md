# Harness State

Updated: 2026-07-09

## Current Snapshot

- Project: k8s-deploy-agent
- Runtime: Claude Code
- Stack: Python 3.11+, uv, pytest
- Current focus: Task 7.1 — clone 모드에서 source_credential_id 없이 anonymous clone 허용
- Task source of truth: `tasks/index.json`

## Active Task

| Task | Status | Notes |
|------|--------|-------|
| 7.1 | done | web.py `_is_public_sample_clone` → `_is_anonymous_clone` 일반화로 해결. config.py는 변경 불필요로 판명. RUN_REPORT.md 참고 |

## Verification Command

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

## Important Constraints

- Preserve air-gapped/on-premise operation.
- Do not introduce external SaaS dependencies.
- Do not place secret values in config, generated files, UI, logs, or tests.
- Existing worktree is dirty; do not revert unrelated user changes.
