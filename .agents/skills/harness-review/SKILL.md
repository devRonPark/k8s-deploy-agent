---
name: harness-review
description: 현재 diff를 Task, CLAUDE.md 규칙, Acceptance evidence 기준으로 코드 리뷰한다. 리뷰 요청이나 PR 전 점검 시 사용.
---

# harness-review

Codex에서 Claude Code `/harness-review`에 해당하는 리뷰 절차를 수행한다.

## 절차

1. `AGENTS.md`, `CLAUDE.md`, `agents/quality-gates.md`, 대상 Task, Acceptance evidence, 현재 diff를 읽는다.
2. Spec compliance 관점으로 Task DoD, Acceptance, TDD evidence, fresh verification evidence, scope/YAGNI 위반을 먼저 확인한다.
3. Code quality 관점으로 버그, 회귀 위험, 누락된 테스트, 유지보수성 문제, `agents/quality-gates.md` 위반을 찾는다.
4. findings를 심각도순으로 먼저 보고하고, 각 항목은 파일·라인 근거를 포함한다.
5. 문제가 없으면 "발견 없음"을 명확히 말하고 남은 테스트 gap이나 잔여 위험만 짧게 남긴다.

## 리뷰 축

- `Spec compliance`: Task 요구, DoD, Acceptance, TDD 또는 예외 사유, fresh verification evidence 충족 여부.
- `Code quality`: 버그, 회귀 위험, 과한 추상화, 불필요한 범위 확장, 테스트 누락 여부.

## 판정

- `APPROVE`: `Spec compliance`와 `Code quality` 모두 blocker 없음, fresh verification evidence가 충분함.
- `REQUEST_CHANGES`: 둘 중 하나라도 blocker가 있음. 동작 버그, 규칙 위반, TDD evidence 누락, Acceptance 미실행/실패, 테스트 누락이 Task 완료를 막으면 이 판정이다.

리뷰 중 직접 수정하지 않는다. 수정이 필요하면 findings를 근거로 구현 단계로 되돌린다.
findings는 `agents/quality-gates.md`의 review/reporting gate처럼 먼저 보고하고,
문제가 없으면 테스트 gap과 잔여 위험만 짧게 남긴다.
