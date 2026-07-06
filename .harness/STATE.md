# Harness State

Updated: 2026-07-06

## Current Snapshot

- Project: k8s-deploy-agent
- Runtime: Codex CLI
- Stack: Python 3.11+, uv, pytest
- Current focus: Dockerfile proposal preview implementation complete on `feature/dockerfile-build-profile`
- Task source of truth: `Plans.md`

## Active Task

| Task | Status | Notes |
|------|--------|-------|
| 3.8-3.12 | cc:완료 | Node/Java/Go Dockerfile proposals, `.dockerignore` proposals, and proposal validation artifacts are complete |

## Verification Command

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

## Important Constraints

- Preserve air-gapped/on-premise operation.
- Do not introduce external SaaS dependencies.
- Do not place secret values in config, generated files, UI, logs, or tests.
- Existing worktree is dirty; do not revert unrelated user changes.
