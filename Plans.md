# Plans.md - k8s-deploy-agent

작성일: 2026-07-06
기준 문서: README.md, docs/demo-scenario.md, docs/ui-ux-plan.md
런타임: Codex CLI

---

## Week 0 - Harness Bootstrap

| Task | 내용 | DoD | Acceptance | Depends | Status | GH |
|------|------|-----|------------|---------|--------|----|
| 0.1 | Codex harness 기본 파일 추가 | AGENTS.md, harness.toml, Plans.md, .harness/ 상태 문서가 존재한다 | test -f AGENTS.md && test -f harness.toml && test -f Plans.md && test -f .harness/STATE.md | - | cc:완료 | - |
| 0.2 | Python CLI 검증 명령 고정 | harness.toml과 AGENTS.md에 uv pytest 명령이 기록된다 | grep -q "uv run pytest -q" AGENTS.md && grep -q "uv run pytest -q" harness.toml | 0.1 | cc:완료 | - |
| 0.3 | GitHub Actions CI 추가 | .github/workflows/ci.yml이 uv 기반 pytest를 실행한다 | test -f .github/workflows/ci.yml && grep -q "uv run pytest -q" .github/workflows/ci.yml | 0.1 | cc:완료 | - |

---

## Week 1 - Operator Console Planning

| Task | 내용 | DoD | Acceptance | Depends | Status | GH |
|------|------|-----|------------|---------|--------|----|
| 1.1 | Local operator console PRD 작성 | docs/PRD.md에 폐쇄망 operator console MVP 범위가 정리된다 | test -f docs/PRD.md | 0.1 | cc:완료 | - |
| 1.2 | UI flow와 architecture 작성 | docs/UserFlow.md와 docs/Architecture.md에 web command, dry-run execution, LLM boundary가 정리된다 | test -f docs/UserFlow.md && test -f docs/Architecture.md | 1.1 | cc:완료 | - |

---

## Week 2 - Local Operator Console

| Task | 내용 | DoD | Acceptance | Depends | Status | GH |
|------|------|-----|------------|---------|--------|----|
| 2.1 | `web` command 기본 local console shell 추가 | `k8s-deploy-agent web --host 127.0.0.1 --port 8080`가 외부 asset 없이 local operator console HTML을 제공한다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 1.2 | cc:완료 | - |
| 2.2 | operator console config form payload 검증 추가 | UI 입력이 `DemoConfig` compatible payload로 검증되고 raw secret-like 값이 거부된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 2.1 | cc:완료 | - |
| 2.3 | operator console dry-run 실행 연결 | web flow가 기존 dry-run pipeline을 재사용해 output directory에 산출물을 생성한다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 2.2 | cc:완료 | - |
| 2.4 | generated asset preview와 validation checklist 추가 | UI가 generated files와 blocking validation 상태를 local output 기준으로 표시한다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 2.3 | cc:완료 | - |

---

## Week 3 - Dockerfile Generation Planning

| Task | 내용 | DoD | Acceptance | Depends | Status | GH |
|------|------|-----|------------|---------|--------|----|
| 3.1 | Dockerfile 자동 생성 범위 정의 | Dockerfile 생성의 입력, 출력, 제한, and validation gate가 문서로 정리된다 | test -f docs/DockerfilePlan.md | 2.4 | cc:완료 | - |
| 3.2 | BuildProfile 데이터 모델 추가 | service별 Dockerfile proposal 전 단계 정보를 담는 BuildProfile 구조가 정의된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.1 | cc:완료 | - |
| 3.3 | repository analyzer BuildProfile 생성 | Python/Node/Java/Go service 후보에서 dependency file, lockfile, build tool, existing Dockerfile evidence가 수집된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.2 | cc:완료 | - |
| 3.4 | runtime command와 port evidence 분석 | analyzer가 runtime command 후보와 port evidence를 confidence와 함께 profile에 기록한다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.3 | cc:완료 | - |
| 3.5 | Dockerfile proposal gate 추가 | low-confidence 또는 unresolved profile은 Dockerfile proposal 대상에서 제외된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.4 | cc:완료 | - |
| 3.6 | BuildProfile 리포트 출력 추가 | repository analysis report와 operator console preview에 BuildProfile evidence와 unresolved questions가 표시된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.5 | cc:완료 | - |
| 3.7 | Python Dockerfile proposal preview 추가 | confirmed Python BuildProfile에서 review-only Dockerfile proposal artifact가 생성된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.6 | cc:완료 | - |
| 3.8 | Node.js Dockerfile proposal preview 추가 | confirmed Node BuildProfile에서 review-only Dockerfile proposal artifact가 생성된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.7 | cc:완료 | - |
| 3.9 | Java Dockerfile proposal preview 추가 | confirmed Java BuildProfile에서 review-only Dockerfile proposal artifact가 생성된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.8 | cc:완료 | - |
| 3.10 | Go Dockerfile proposal preview 추가 | confirmed Go BuildProfile에서 review-only Dockerfile proposal artifact가 생성된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.9 | cc:완료 | - |
| 3.11 | `.dockerignore` proposal preview 추가 | BuildProfile 기반 ignore 후보가 review-only `.dockerignore` proposal artifact로 생성된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.10 | cc:완료 | - |
| 3.12 | Dockerfile proposal validation checklist 추가 | generated Dockerfile/.dockerignore proposals가 secret redaction, confidence gate, source write-back 없음 조건으로 검증된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.11 | cc:완료 | - |

---

## Week 4 - Repository Shape Coverage

| Task | 내용 | DoD | Acceptance | Depends | Status | GH |
|------|------|-----|------------|---------|--------|----|
| 4.1 | root-level app repository 감지 추가 | repository root에 `package.json`, `pyproject.toml`, `requirements.txt`, `pom.xml`, `build.gradle`, 또는 `go.mod`가 있는 단일 앱 repo가 서비스 후보와 BuildProfile로 감지된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.12 | cc:완료 | - |

---

## Week 5 - Web Local Source Input

| Task | 내용 | DoD | Acceptance | Depends | Status | GH |
|------|------|-----|------------|---------|--------|----|
| 5.1 | web form에서 local repo path 분석 지원 | clone/local mode 선택, local path validation, dry-run asset generation, source repo write-back 없음 조건이 구현된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 2.4 | cc:완료 | - |

---

## Week 6 - Operator Console UX

| Task | 내용 | DoD | Acceptance | Depends | Status | GH |
|------|------|-----|------------|---------|--------|----|
| 6.1 | operator console 단계형 UI/UX 개편 | web console이 입력, 검증, dry-run, 분석/산출물 리뷰, checklist를 단계형 workflow로 보여주고 generated asset preview를 기능별로 묶는다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 5.1 | cc:완료 | - |

---

<!--
Task 상태의 단일 출처는 tasks/index.json이다.
Plans.md는 사람이 필요할 때 python3 scripts/sync_plans.py로 갱신하는
읽기용 snapshot이며 stale일 수 있다. 상태 판단과 CI 검증은 항상
tasks/index.json을 기준으로 한다.

JSON status 값:
  todo    — 미시작 (Plans.md 표시: cc:TODO)
  wip     — 진행 중 (Plans.md 표시: cc:WIP)
  done    — 완료 (Plans.md 표시: cc:완료)
  blocked — 차단됨 (Plans.md 표시: cc:BLOCKED, blocked_reason 필수)

GH 컬럼:
  -         — GitHub 미연동 또는 이슈 미생성
  #N        — 연결된 GitHub Issue 번호 (harness-plan이 자동 기입)

Acceptance 컬럼:
  -         — 기계 검증 없음 (skip). "|| echo skip"처럼 항상 성공하는
              패턴은 oracle을 무력화하므로 금지 — 검증 안 할 거면 "-"로 명시.
  명령어     — 세션 에이전트가 완료 전 실행, 실패하면 done 전환 금지.
              CI checkout 범위 밖 경로(예: ../다른-repo/)는 실행 불가 — 금지.
              Given=repo checkout/Depends 산출물, When=명령 실행, Then=exit 0
              또는 출력·파일·응답 검증이 되도록 쓴다.
  예시: pytest tests/test_auth.py -k login
  예시: curl -sf http://localhost/health | grep '"status":"ok"'
  패턴별 예시:
    파일 존재: test -f src/main.py
    명령 성공: npm run build 2>&1 | grep -v error
    HTTP 응답: curl -sf http://localhost:3000/health | grep ok
    테스트 통과: pytest tests/ -x -q
    출력 포함: go test ./... | grep -v SKIP
  escaped pipe(예: grep 'a\|b')는 Acceptance 컬럼에서만 사용 — DoD 등 다른
  컬럼에 쓰면 파서가 열 개수를 오인식한다.
  * GitHub CI 스택 설치(npm ci 등)는 .github/workflows/ci.yml에서 설정

DoD (Definition of Done) 작성 원칙:
  - 검증 가능한 파일·명령·출력으로 기술
  - "존재한다", "성공한다", "에러 0"처럼 객관적 기준
  - "잘 작성된다", "좋다"처럼 주관적 기준 금지
  - INVEST 기준: 독립 검증 가능, 관찰 가능한 가치, 1 PR 이내, 테스트 가능
-->
