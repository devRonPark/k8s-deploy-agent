# k8s-deploy-agent — CLAUDE.md

Claude Code 기준 rulebook이다. Codex는 `AGENTS.md`와 `.agents/skills/*`로 같은 절차를 수행한다.

## 프로젝트 기본값

- 프로젝트: on-premise Kubernetes migration preparation agent
- 런타임: Python 3.11+, Codex CLI
- 패키지 관리자: uv
- 엔트리포인트: `k8s-deploy-agent`
- 기본 검증: `UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q`
- 배포 대상: customer on-premise or air-gapped environments
- 응답 언어: 한국어. 코드, 명령어, 고유명사는 그대로 둔다.
- 코딩 규칙: Python standard library 우선, deterministic dry-run, raw secret value 금지, generated asset write-back은 explicit validation gate 뒤에서만 허용.
- local `web` 시작은 기본적으로 `127.0.0.1:8080`을 사용한다. 사용자가 다른 포트를 요구하지 않으면 변경하지 않는다.

## 핵심 파일

| 파일 | 역할 |
|---|---|
| `tasks/index.json` | Task 상태 단일 출처 |
| `Plans.md` | `tasks/index.json`에서 생성한 읽기용 snapshot |
| `harness.toml` | harness 설정과 규칙 요약 인덱스 |
| `agents/quality-gates.md` | scope/YAGNI/review/reporting 공통 gate |
| `agents/task-decomposer.md` | 세분화 게이트 |
| `agents/test-agent.md` | Acceptance와 관련 테스트 실행 절차 |
| `.harness/tasks/<task-key>/` | live task 맥락 |

## 기획 규칙

- 새 프로젝트/기능 착수 시 코드보다 먼저 `/grill-me`를 실행한다.
- 핵심 흐름: spec -> plan -> isolated work -> TDD -> fresh verification -> review -> finish.
- 기획 흐름: 인터뷰 -> `docs/PRD.md` 초안 -> 필요한 보완 문서 -> `/harness-plan`.
- 보완 문서는 `docs/templates/{UserFlow,DESIGN,Architecture}.md` 중 필요한 것만 복사한다.
- UI가 있으면 `docs/DESIGN.md`를 UI 구현의 single source of truth로 둔다. UI 없는 프로젝트는 생략한다.
- 확정 결정은 PRD의 Decisions 섹션에 기록한다. ADR은 큰 결정이 쌓일 때만 만든다.

## Planning Proposal Gate

`/harness-plan`이 `tasks/index.json`에 Task를 쓰기 전 반드시 proposal 단계를 거친다.

1. `scripts/build_planning_context.py`로 `.harness/shared/planning/runs/{run_id}/context.json`을 만든다.
2. 기본은 현재 세션이 `agents/task-decomposer.md` 기준으로 proposal 계약을 채우는 inline 흐름이다.
3. `harness.toml [plan].decomposer_command`가 있으면 외부 명령이 `proposed-tasks.json`과 `decomposition-report.md`를 만들 수 있다. 명령이 없거나 실패하면 `.harness/events/planning.jsonl`에 쉬운 실패 메시지를 남기고, `allow_inline_fallback = true`일 때 현재 세션이 이어서 채운다.
4. `scripts/validate_task_proposal.py`가 기존 Task와 proposal을 합쳐 검증한다.
5. 통과한 경우에만 `scripts/apply_task_proposal.py`로 반영한다. 반영 후 `Plans.md`는 자동 재생성된다.

Planning 로그의 최상위 `step`, `result`, `message`, `next_action`은 사용자가 이해할 문장으로 쓴다. 내부 이벤트명, run id, 파일 목록은 `technical` 하위에 둔다.

## 상태 문서 규칙

- 터미널 세션은 언제든 끊길 수 있다고 가정한다.
- 작업 시작 전과 의미 있는 작업 단위 후 `.harness/tasks/<task-key>/STATE.md`를 갱신한다.
- Task 상태는 `tasks/index.json`만 믿는다. `.harness/tasks/<task-key>/`는 세션 맥락만 담는다.
- 루트 `.harness/{STATE,HANDOFF,TASKS,LOG,CHECKPOINTS,RUN_REPORT}.md`는 새 Task용 템플릿이다.
- 새 Task 착수 시 루트 템플릿을 `.harness/tasks/<task-key>/`로 복사한다. 필요하면 `tasks.index.snapshot.json`도 저장한다.
- 세션 재개 읽기 순서: `tasks/index.json` -> `.harness/tasks/<task-key>/STATE.md` -> 있으면 `RUN_REPORT.md` -> `.harness/LESSONS.md` 최근 항목 -> `Plans.md` -> 필요한 파일만 `.harness/CONTEXT_INDEX.md`에서 선택.
- 에러는 Task `LOG.md`에 원문 기록한다. 반복 방지 규칙은 `.harness/LESSONS.md`에 남긴다.
- 새 파일을 만들거나 파일 역할이 바뀌면 `.harness/CONTEXT_INDEX.md`를 갱신한다.
- 요청이 전제한 파일이 없으면 임의 생성하지 말고 사용자에게 보고한다.

## GitHub 플로우

`harness.toml [github].enabled = true`일 때만 적용한다. 미사용이면 이 섹션은 무시해도 된다.

- 브랜치: `task/{task-id}-{short-slug}`
- 커밋: `task {task-id}: {summary}`
- Planning: Week는 Milestone, Task는 Issue로 만들고 issue 번호를 `tasks/index.json`의 `gh`에 `#N`으로 기록한다.
- Implementation: task branch 생성 -> 해당 Task를 `wip`로 변경 -> 구현 -> Acceptance/test -> review -> PR.
- PR: 연결 이슈가 있으면 `Closes #N`을 본문에 포함한다.
- Merge 조건: `ci-ok`, `plans-guard`, PR 승인.
- 완료 전환: Acceptance와 관련 테스트가 통과하면 세션 에이전트가 `tasks/index.json`을 `done`으로 갱신하고 `python3 scripts/sync_plans.py`를 실행한다. GitHub Actions는 Task 상태를 바꾸지 않는다.
- CI 설정: `.github/workflows/ci.yml`의 기술 스택 블록을 프로젝트에 맞게 켠다.

## 구현 규칙 (세분화 게이트)

- 외부 SaaS 호출, 원격 telemetry, secret value 저장, source/GitOps write-back 자동 실행은 금지한다.
- credential은 raw value가 아니라 credential ID 또는 environment variable name으로 표현한다.
- Kubernetes, Jenkins, Fleet, Dockerfile 산출물은 operator review가 쉬운 단순한 형태를 우선한다.
- 구현 전 `agents/quality-gates.md`를 scope/YAGNI gate로 적용한다.
- `/harness-work` 실행 전 대상 `todo` Task가 `agents/task-decomposer.md`의 세분화 기준을 통과했는지 확인한다.
- DoD/Acceptance 미기재, 뭉뚱그린 표현, 여러 관심사 혼재, 1 PR 초과 징후가 있으면 구현하지 않는다. `/harness-plan`으로 하위 Task proposal을 먼저 만든다.
- 작업 중 범위가 커지면 멈추고 `agents/task-decomposer.md`와 `agents/quality-gates.md` 기준으로 재분해한다.
- 기능, 버그 수정, 동작 변경은 TDD가 기본 완료 조건이다. 먼저 실패하는 테스트나 Acceptance evidence를 확인하고, 최소 구현 후 green을 확인해야 한다.
- 문서, 설정, 생성 코드, throwaway prototype처럼 TDD가 맞지 않는 변경은 예외로 둘 수 있지만, 예외 이유를 `.harness/tasks/<task-key>/RUN_REPORT.md` Evidence 또는 Notes에 남긴다.
- 큰 Task이거나 리뷰 리스크가 높으면 implementer/reviewer subagent 사용을 선택형 gate로 제안한다. ledger나 `.superpowers/` 디렉토리는 만들지 않는다.
- `plans-guard.yml`은 구조와 sync만 검증한다. 세분화와 YAGNI 판단은 현재 세션의 책임이다.

## 테스트 규칙

- worker 구현 완료 후 reviewer 검토 전에 `agents/test-agent.md` 절차를 실행한다.
- 해당 Task의 Acceptance 명령과 관련 프로젝트 테스트 스위트를 모두 실행한다.
- 완료, 통과, 수정 완료, PR 가능 같은 성공 주장은 구현 이후 fresh verification evidence가 있을 때만 허용한다.
- Acceptance가 통과해도 TDD evidence 또는 예외 사유가 없으면 리뷰에서 `REQUEST_CHANGES`가 가능하다.
- Verdict FAIL이면 reviewer에 넘기지 않는다. 실패 내용을 근거로 수정 후 재실행한다.

## 리뷰 규칙

- worker 완료 후 PR 오픈 전에 `/harness-review`를 실행한다.
- 리뷰는 `agents/quality-gates.md`의 review/reporting gate를 따른다.
- findings를 먼저 보고하고 TDD, Acceptance/test, fresh verification evidence와 잔여 risk를 짧게 남긴다.
- verdict는 `Spec compliance`와 `Code quality` 두 축을 따로 본다. 둘 중 하나라도 blocker면 전체 판정은 `REQUEST_CHANGES`다.
- `REQUEST_CHANGES` 상태에서 PR을 열지 않는다.

## Finish 규칙

- finish는 검증과 리뷰가 끝난 뒤에만 말한다. `RUN_REPORT.md` Evidence 표가 완료 판정의 근거다.
- merge, PR, branch keep/discard 같은 선택지는 사용자가 명시 요청할 때만 제시한다.
