# Harness Handoff

## Next Session Start

1. Read `AGENTS.md`.
2. Read `.harness/STATE.md`.
3. Read recent entries in `.harness/LESSONS.md`.
4. Check `Plans.md` for the active task.
5. Run the relevant Acceptance command before marking work complete.

## Current Handoff

Harness bootstrap is being adapted for Codex CLI. Claude-specific runtime files from the template are intentionally not copied as active configuration.

The project-specific command to verify behavior is:

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```
