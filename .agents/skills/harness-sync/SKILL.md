---
name: harness-sync
description: tasks/index.json을 검증하고 Plans.md snapshot을 재생성한다. 계획 동기화, snapshot 갱신 요청 시 사용.
---

# harness-sync

`tasks/index.json`을 검증하고 `Plans.md` 읽기용 snapshot을 최신화한다.

## 절차

1. `AGENTS.md`, `CLAUDE.md`, `tasks/index.json`, `Plans.md`를 읽는다.
2. `python3 scripts/validate_tasks.py`를 실행한다.
3. 검증이 통과하면 `python3 scripts/sync_plans.py`를 실행한다.
4. 다시 `python3 scripts/sync_plans.py --check`로 동기화 여부를 확인한다.

## 규칙

- `Plans.md`는 생성물이다. 직접 편집하지 않는다.
- 검증 실패 시 `Plans.md`를 갱신하지 말고 실패 원인과 수정 필요 지점을 보고한다.
