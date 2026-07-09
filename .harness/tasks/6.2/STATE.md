# Harness State

Updated: 2026-07-09 13:57 KST

## Current Snapshot

- Project: k8s-deploy-agent
- Runtime: Codex CLI
- Stack: Python 3.11+, uv, pytest
- Current focus: Task 6.2 web console public GitHub sample clone preset
- Task source of truth: `tasks/index.json`

## Active Task

| Task | Status | Notes |
|------|--------|-------|
| 6.2 | done | Added a no-JS web console sample preset and a follow-up first-test path where 작업 대상 + Source repository 입력만으로 web validation/local dry-run passes using review-only GitOps placeholders. |

## Gate Check

- Task decomposer: pass. Single web form contract change, one acceptance command, depends on completed 6.1.
- Scope/YAGNI: pass. Reuse existing HTML form, validation, dry-run pipeline, and pytest tests. No external SaaS runtime call, no write-back behavior.
- TDD requirement: satisfied. Related regression tests failed before implementation and passed after implementation.
- Fresh verification: `UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q` passed with 49 tests.
- Review: APPROVE. No Spec compliance or Code quality blockers found.

## Verification Command

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

## Important Constraints

- Preserve air-gapped/on-premise operation.
- Do not introduce external SaaS dependencies.
- Do not place secret values in config, generated files, UI, logs, or tests.
- Existing untracked `demo-test-output-config-source/` is unrelated and must not be reverted or modified.
