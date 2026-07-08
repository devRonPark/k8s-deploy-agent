# Harness State

Updated: 2026-07-08

## Current Snapshot

- Project: k8s-deploy-agent
- Runtime: Codex CLI
- Stack: Python 3.11+, uv, pytest
- Current focus: operator console step-based UI/UX refresh complete
- Task source of truth: `Plans.md`

## Active Task

| Task | Status | Notes |
|------|--------|-------|
| 6.1 | cc:완료 | Web console presents input, validation, dry-run, review, and checklist as a step-based operator workflow |

## Verification Command

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

## Important Constraints

- Preserve air-gapped/on-premise operation.
- Do not introduce external SaaS dependencies.
- Do not place secret values in config, generated files, UI, logs, or tests.
- Existing worktree is dirty; do not revert unrelated user changes.
