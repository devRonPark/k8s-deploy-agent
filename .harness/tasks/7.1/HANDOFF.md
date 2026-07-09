# Harness Handoff

## Next Session Start

1. Read `AGENTS.md`.
2. Read `CLAUDE.md`.
3. Check `tasks/index.json` for the active task.
4. Read `.harness/STATE.md` and recent entries in `.harness/LESSONS.md`.
5. Use `Plans.md` as a generated snapshot only.
6. Run the relevant Acceptance command before marking work complete.

## Current Handoff

`cc-harness-template` v4 structure has been applied. Durable task status now lives in `tasks/index.json`, and `Plans.md` is regenerated with `python3 scripts/sync_plans.py`.

The project-specific command to verify behavior is:

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```
