# Test Agent

Purpose: verify implementation before review or completion.

This is a Codex CLI procedure document. Run the commands directly in the repository root.

## Inputs

- `task_id`: `Plans.md` task ID
- `acceptance`: command from the `Acceptance` column
- `worktree_path`: repository root, normally current directory

## Procedure

1. Run the task Acceptance command when it is not `-`.
2. Run the project test suite.
3. Report PASS/FAIL with the failing command if anything fails.

## Project Test Suite

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

## Result Format

```text
Test Agent Report - Task {task_id}
Acceptance : PASS|SKIP|FAIL ({command})
Test suite : PASS|FAIL (pytest)
Verdict    : PASS|FAIL
```

## Failure Rule

If Acceptance or tests fail, do not mark the task complete. Fix the issue, rerun the command, and record reusable prevention rules in `.harness/LESSONS.md` when applicable.
