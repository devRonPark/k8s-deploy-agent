# Task Decomposer

Purpose: convert broad planning items into small, executable `Plans.md` rows before implementation starts.

This is a procedure document for Codex CLI. It is not a separate executable agent.

## When To Use

Use this document when:

- a requested task touches multiple concerns
- a `Plans.md` task lacks objective DoD or Acceptance
- a task includes broad wording such as "전체", "모든", "및", "그리고"
- implementation would require unrelated changes across three or more files
- work should be split before a PR or commit

## Granularity Criteria

A task is small enough when all are true:

- It changes one concern: analysis, config parsing, Jenkins generation, GitOps generation, UI, docs, tests, or CI.
- It has one primary artifact or behavior.
- It can be verified independently.
- It is likely one focused commit or PR.
- It has an objective DoD and a runnable Acceptance command.

If any criterion fails, split the task.

## Output Format

Add or propose rows in this format:

```markdown
| Task | 내용 | DoD | Acceptance | Depends | Status | GH |
|------|------|-----|------------|---------|--------|----|
| 1.1 | ... | ... | ... | ... | cc:TODO | - |
```

## Project-Specific Examples

Good:

```markdown
| 2.1 | dry-run web form에서 config 값을 수집한다 | web form submit이 DemoConfig-compatible payload를 만든다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 1.2 | cc:TODO | - |
```

Too broad:

```markdown
| 2.1 | operator console 전체 구현 | UI와 LLM과 write-back이 동작한다 | - | - | cc:TODO | - |
```

Split broad UI work into config input, dry-run execution, preview, validation checklist, and LLM review panel.
