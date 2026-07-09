---
description: PRD·기획 문서를 실행 가능한 Task proposal로 분해하고 검증 후 tasks/index.json에 반영한다.
allowed-tools: Read, Bash(python3 scripts/build_planning_context.py:*), Bash(python3 scripts/validate_task_proposal.py:*), Bash(python3 scripts/apply_task_proposal.py:*), Bash(python3 scripts/sync_plans.py:*), Bash(python3 scripts/validate_tasks.py:*), Bash(git status:*), Bash(git branch:*)
---

# /harness-plan

절차 원본은 `.agents/skills/harness-plan/SKILL.md`다. 이 command는 Claude Code 호출용 wrapper다.

1. `.agents/skills/harness-plan/SKILL.md`를 읽고 같은 절차를 따른다.
2. `AGENTS.md`, `CLAUDE.md`, `agents/quality-gates.md`, `tasks/index.json`, `Plans.md`, 필요한 기획 문서를 읽는다.
3. `python3 scripts/build_planning_context.py`로 planning context를 만든다.
4. 현재 세션이 `agents/task-decomposer.md` 기준으로 proposal 파일 계약을 채운다. `harness.toml [plan].decomposer_command`가 있으면 외부 명령에 위임하고, 실패하면 쉬운 실패 로그를 남기고 inline fallback으로 돌아온다.
5. `python3 scripts/validate_task_proposal.py ...`로 proposal을 검증한다.
6. 통과한 경우에만 `python3 scripts/apply_task_proposal.py ...`로 `tasks/index.json`에 반영한다.
7. `python3 scripts/sync_plans.py`로 `Plans.md`를 재생성하고 `python3 scripts/validate_tasks.py`로 확인한다.
8. proposal은 검증 전까지 확정본이 아니다. `tasks/index.json`을 검증 없이 직접 수정하지 않는다.
9. 새 Task는 `agents/task-decomposer.md`의 INVEST·DoD·Acceptance 기준과 `agents/quality-gates.md`의 scope/YAGNI 기준을 만족해야 한다.
10. 인자: `$ARGUMENTS`
