# BLUEPRINT.md — Claude Code / Codex Harness 구조

이 문서는 구조 색인이다. 실행 규칙의 단일 출처는 `CLAUDE.md`이고, Codex 호환 절차는 `AGENTS.md`와 `.agents/skills/*`가 맡는다.

## 최소 성공 흐름

1. spec: 목표, 제약, 성공 기준을 한 문단으로 적는다.
2. plan: `tasks/index.json`에 작은 Task, DoD, Acceptance를 둔다.
3. isolated work: 구현 전 `agents/task-decomposer.md`와 `agents/quality-gates.md`를 확인한다.
4. TDD: 동작 변경은 실패하는 테스트나 Acceptance evidence를 먼저 확인한다.
5. fresh verification: 구현 후 Acceptance와 관련 테스트를 새로 실행한다.
6. review: `Spec compliance`와 `Code quality`를 분리해 확인한다.
7. finish: 실패는 `.harness/tasks/<task-key>/LOG.md`, 완료 요약과 evidence는 `RUN_REPORT.md`에 남긴 뒤 `tasks/index.json`과 `Plans.md`를 갱신한다.

## 레이어

```
사용자 요청
  -> CLAUDE.md / AGENTS.md 규칙 확인
  -> tasks/index.json에서 대상 Task 선택
  -> agents/* gate 적용
  -> 구현, TDD, fresh verification, 리뷰
  -> Plans.md snapshot 갱신
```

## 파일 역할

| 파일 | 역할 |
|---|---|
| `CLAUDE.md` | Claude Code 기준 rulebook. 기획, 구현, 테스트, 리뷰, 상태 문서 규칙의 원본 |
| `AGENTS.md` | Codex 진입점. Claude slash workflow를 Codex skill로 매핑 |
| `harness.toml` | harness 설정과 `[github]`, `[review]`, `[test]`, `[plan]` 요약 인덱스 |
| `tasks/index.json` | Task 상태 단일 출처 |
| `Plans.md` | `tasks/index.json`에서 생성한 사람용 snapshot |
| `.harness/` | Task별 재개 맥락, planning 이벤트, 템플릿 |
| `agents/quality-gates.md` | Claude/Codex 공통 scope, YAGNI, review, reporting gate |
| `agents/task-decomposer.md` | Task 세분화 게이트 |
| `agents/test-agent.md` | Acceptance와 관련 테스트 실행 절차 |
| `.agents/skills/` | Codex repo-scoped skills |
| `.claude/commands/` | Claude Code local commands |
| `.github/workflows/` | CI와 plans guard |
| `scripts/` | task 검증, planning proposal, Plans sync 도구 |

## Claude Code와 Codex 차이

Claude Code는 plugin과 slash command를 사용할 수 있다. Codex는 plugin hook을 자동으로 받지 않으므로 `AGENTS.md`와 `.agents/skills/*`를 통해 같은 절차를 직접 수행한다.

ponytail/caveman의 durable 원칙은 Codex에서 별도 plugin으로 실행된다고 가정하지 않는다. 공통 기준은 `agents/quality-gates.md`다.

## 수행 주체

`agents/*.md`는 호출 가능한 Claude 서브에이전트 파일이 아니라 절차 문서다. 수행 주체는 현재 세션의 Claude Code 또는 Codex다. planning은 inline proposal이 기본이고, 외부 실행은 `harness.toml [plan].decomposer_command`가 있을 때만 위임한다.

## Planning

`/harness-plan` 또는 `$harness-plan`은 다음 순서를 따른다.

1. `scripts/build_planning_context.py`로 `.harness/shared/planning/runs/{run_id}/context.json` 생성
2. 현재 세션이 proposal 작성
3. `decomposer_command`가 있으면 외부 명령으로 proposal 생성을 위임할 수 있음
4. `scripts/validate_task_proposal.py`로 검증
5. `scripts/apply_task_proposal.py`로 `tasks/index.json` 반영과 `Plans.md` 재생성

## Implementation

`/harness-work` 또는 `$harness-work`는 다음 게이트를 통과해야 한다.

1. `todo` Task 선택
2. `agents/task-decomposer.md` 세분화 게이트 확인
3. `agents/quality-gates.md` scope/YAGNI 확인
4. `.harness/tasks/<task-key>/STATE.md` 갱신
5. TDD red evidence 확인 또는 예외 사유 기록
6. 구현
7. Acceptance와 관련 테스트를 fresh verification으로 실행
8. 리뷰
9. 통과 시 `tasks/index.json` 상태 변경과 `Plans.md` 재생성

Actions는 Task 상태를 쓰지 않고 PR 검증만 수행한다.

## GitHub 통합

`harness.toml [github].enabled = true`일 때만 적용한다. 상세 절차는 `CLAUDE.md`와 `docs/github-integration.md`를 따른다.

| 항목 | 기준 |
|---|---|
| 브랜치 | `task/{task-id}-{short-slug}` |
| 커밋 | `task {task-id}: {summary}` |
| PR | `gh pr create --draft`, 연결 이슈가 있으면 `Closes #N` |
| 필수 check | `ci-ok`, `plans-guard` |

## 명령 매핑

| 목적 | Claude Code | Codex |
|---|---|---|
| 기획 인터뷰 | `/grill-me` | `$grill-me` |
| Task 추가 | `/harness-plan` | `$harness-plan` |
| Task 구현 | `/harness-work` | `$harness-work` |
| 리뷰 | `/harness-review` | `$harness-review` |
| 진행 확인 | `/harness-progress` | `$harness-progress` |
| Plans sync | `/harness-sync` | `$harness-sync` |
| 브랜치 전환 | `/branch-checkout` | `$branch-checkout` |
| push | `/git-push` | `$git-push` |
| PR 생성 | `/pr-create` | `$pr-create` |
| main 작업 구조 | `/rescue-from-main` | `$rescue-from-main` |

## 남긴 확장 지점

- `scripts/run_task_decomposer.py`: planning proposal 외부 명령 계약 확인용. 새 프로젝트 기본 복사에서는 제외
- `.github/workflows/ci.yml`: 프로젝트별 스택 테스트 블록 활성화용
- `.github/workflows/plans-guard.yml`: `tasks/index.json`과 `Plans.md` 드리프트 방지
