---
name: harness-plan
description: PRD·기획 문서를 실행 가능한 Task proposal로 분해하고 검증 후 tasks/index.json에 반영한다. Task 추가·변경이나 계획 수립 요청 시 사용.
---

# harness-plan

Codex에서 Claude Code `/harness-plan`에 해당하는 절차를 직접 수행한다. `Plans.md`를
직접 편집하지 않는다.

## 절차

1. `AGENTS.md`, `CLAUDE.md`, `agents/quality-gates.md`, `tasks/index.json`, `Plans.md`, 필요한 기획 문서를 읽는다.
2. `python3 scripts/build_planning_context.py`로 planning context를 만든다.
3. 현재 Codex 세션이 `agents/task-decomposer.md` 기준으로 proposal 파일 계약을 채운다.
4. `harness.toml [plan].decomposer_command`가 명시되어 있으면 외부 명령으로 proposal 생성을 위임할 수 있다. 실패하면 쉬운 실패 로그를 남기고 inline fallback으로 돌아온다.
5. `python3 scripts/validate_task_proposal.py ...`로 proposal을 검증한다.
6. 통과한 경우에만 `python3 scripts/apply_task_proposal.py ...`로 `tasks/index.json`에 반영한다.
7. `python3 scripts/sync_plans.py`로 `Plans.md`를 재생성하고 `python3 scripts/validate_tasks.py`로 확인한다.

## 규칙

- proposal은 확정본이 아니다. 검증 전에는 `tasks/index.json`을 수정하지 않는다.
- `.harness/events/planning.jsonl`의 사용자-facing 메시지는 쉬운 문장으로 남긴다.
- 새 Task는 `agents/task-decomposer.md`의 INVEST·DoD·Acceptance 기준과
  `agents/quality-gates.md`의 scope/YAGNI 기준을 만족해야 한다.
- 각 Task는 Files, Interfaces, Verification 관점이 DoD 또는 Acceptance에 드러나야 한다.
- 2-5분 단위 코드 step까지 쪼개지 않는다. 독립 검증 가능한 1 PR 이내 단위면 충분하다.
- placeholder, no-op, 실패를 숨기는 Acceptance는 proposal에 넣지 않는다.
