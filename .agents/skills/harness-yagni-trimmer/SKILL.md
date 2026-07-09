---
name: harness-yagni-trimmer
description: Harness template or harness system YAGNI review for solo builders. Use when the user asks to review, trim, simplify, archive, or reduce a harness/template/system where documentation, progress tracking, logs, reports, workflows, prompts, skills, or task/state files feel too heavy; especially when the goal is complexity reduction rather than feature addition.
---

# harness-yagni-trimmer

Review a harness template from the position of a solo builder. The goal is not to add capability. The goal is to leave only the structure that helps someone quickly resume, code, verify, and move on.

## Core Standard

First answer this before judging files:

```text
What is this harness template's minimum successful flow?
```

Example:

```text
1. Start a new project.
2. Write the goal in one paragraph.
3. Ask Codex to implement.
4. Run the result.
5. If it fails, record only the error and next action.
6. If it succeeds, record changed files and usage.
```

Treat anything not directly helping that flow as suspicious.

## Scan Targets

Prioritize these surfaces:

- `README.md`, `CLAUDE.md`, `AGENTS.md`, `SKILL.md`
- `.codex/`, `.claude/`, `.cursor/`, `.agents/`
- `docs/`, `specs/`, `memory/`, `logs/`, `reports/`, `tasks/`, `workflows/`
- `scripts/`, `templates/`, `prompts/`
- `Makefile`, `package.json`, `pyproject.toml`
- CI/CD configuration files

## Classification

Classify each important file or feature as one of:

- `KEEP`: directly needed in the current solo-builder flow; removing it often blocks work.
- `SIMPLIFY`: needed, but too long, repetitive, or heavy; shorten the format.
- `REMOVE`: not needed now; looks useful but does not change today's work.
- `ARCHIVE`: maybe useful as reference, but should not be in the default harness path.

Default stance: ask "why keep this?" If the answer is weak, mark it `REMOVE` or `ARCHIVE`.

## Preferred Minimal Docs

Reduce default documentation toward these files when safe:

- `README.md`: what this is, how to run it, key commands, current state. Target under 100 lines.
- `WORKING_STATE.md`: current goal, done, next, blockers, last updated.
- `DECISIONS.md`: only hard-to-reverse structural or technical decisions.
- `ERRORS.md`: only recurring errors with symptom, cause, fix, and command.

Do not add these files just to satisfy the pattern if the repo already has a smaller effective equivalent. Consolidate only when it reduces real reading and writing burden.

## Removal Priority

Trim in this order:

1. Duplicate status docs such as `STATUS.md`, `PROGRESS.md`, `TASKS.md`, `REPORT.md`, `WORKING_STATE.md`.
2. Reporting docs such as long completion reports, generated summaries, heavy review logs, retrospectives.
3. Unused expansion structures such as provider abstractions, plugin registries, hook systems, policy layers, generic executors, template engines.
4. Mandatory checklists that do not prevent real mistakes within 30 seconds.
5. Logs that are not failure cause, reproduction command, or next action.

## Workflow

1. Scan the repository and report:

```md
## Harness Surface Area

- 문서 파일 수:
- workflow 파일 수:
- prompt/skill 파일 수:
- logs/reports/tasks 관련 파일 수:
- 의심되는 중복 영역:
```

2. Diagnose briefly:

```md
## Diagnosis

현재 harness는 다음 문제가 있다.

1. 과한 문서화:
2. 중복 상태 추적:
3. 아직 필요 없는 확장 구조:
4. solo builder 흐름 방해 요소:
5. 삭제해도 안전해 보이는 것:
```

3. Apply YAGNI questions to major components:

```md
## YAGNI Questions

### 대상: 파일 또는 기능 이름

- 지금 실제로 쓰는가?
- 없으면 오늘 작업이 막히는가?
- 다음 행동을 더 쉽게 만드는가?
- 같은 내용을 다른 곳에서도 기록하는가?
- 미래 대비라는 이유만으로 존재하는가?

판정:
- KEEP / SIMPLIFY / REMOVE / ARCHIVE

이유:
- 짧게 작성
```

4. Show a trim plan before risky deletion:

```md
## Trim Plan

### KEEP

- 유지할 것

### SIMPLIFY

- 줄일 것
- 어떻게 줄일 것

### REMOVE

- 삭제할 것
- 삭제해도 되는 이유

### ARCHIVE

- 옮길 것
- 이동 위치
```

5. Apply clearly safe reductions without waiting for extra confirmation. Safe examples: merging duplicate docs, deleting empty templates, archiving unused examples, shortening long docs, consolidating duplicate state docs.

6. Do not directly apply risky reductions. Propose first when a change removes execution scripts, CI/CD behavior, real code paths, active hooks, or agent execution rules.

## Final Report

After edits, report exactly in this shape:

```md
# Harness Trim Result

## 한 줄 결론

이번 변경으로 harness가 더 가벼워졌는지 한 문장으로 설명.

## 제거한 것

- 항목:
  - 이유:

## 줄인 것

- 항목:
  - 기존:
  - 변경:

## 남긴 것

- 항목:
  - 이유:

## 아직 무거운 부분

- 항목:
  - 왜 아직 무거운지:
  - 다음에 줄이는 방법:

## 다음 작업

1. 가장 먼저 할 일
2. 그 다음 할 일
3. 보류할 일
```

## Guardrails

- Do not add new harness structures because they look useful.
- Do not create interfaces, providers, plugin registries, or logging frameworks for future use.
- Do not solve documentation bloat by adding more documentation files.
- Do not keep anything only because it might be useful later.
- Judge success by whether the next solo-builder action is easier, not by whether the file count is lower.
