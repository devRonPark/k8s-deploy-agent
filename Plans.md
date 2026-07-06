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

## Week 1 - Operator Console Planning

| Task | 내용 | DoD | Acceptance | Depends | Status | GH |
|------|------|-----|------------|---------|--------|----|
| 1.1 | Local operator console PRD 작성 | docs/PRD.md에 폐쇄망 operator console MVP 범위가 정리된다 | test -f docs/PRD.md | 0.1 | cc:완료 | - |
| 1.2 | UI flow와 architecture 작성 | docs/UserFlow.md와 docs/Architecture.md에 web command, dry-run execution, LLM boundary가 정리된다 | test -f docs/UserFlow.md && test -f docs/Architecture.md | 1.1 | cc:완료 | - |

## Week 2 - Local Operator Console

| Task | 내용 | DoD | Acceptance | Depends | Status | GH |
|------|------|-----|------------|---------|--------|----|
| 2.1 | `web` command 기본 local console shell 추가 | `k8s-deploy-agent web --host 127.0.0.1 --port 8080`가 외부 asset 없이 local operator console HTML을 제공한다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 1.2 | cc:완료 | - |
| 2.2 | operator console config form payload 검증 추가 | UI 입력이 `DemoConfig` compatible payload로 검증되고 raw secret-like 값이 거부된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 2.1 | cc:완료 | - |
| 2.3 | operator console dry-run 실행 연결 | web flow가 기존 dry-run pipeline을 재사용해 output directory에 산출물을 생성한다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 2.2 | cc:완료 | - |
| 2.4 | generated asset preview와 validation checklist 추가 | UI가 generated files와 blocking validation 상태를 local output 기준으로 표시한다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 2.3 | cc:완료 | - |

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

## Week 4 - Repository Shape Coverage

| Task | 내용 | DoD | Acceptance | Depends | Status | GH |
|------|------|-----|------------|---------|--------|----|
| 4.1 | root-level app repository 감지 추가 | repository root에 `package.json`, `pyproject.toml`, `requirements.txt`, `pom.xml`, `build.gradle`, 또는 `go.mod`가 있는 단일 앱 repo가 서비스 후보와 BuildProfile로 감지된다 | UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q | 3.12 | cc:완료 | - |

---

<!--
Task Status:
  cc:TODO   - not started
  cc:WIP    - in progress
  cc:완료   - complete

Acceptance:
  Use a command that can run from repository root.
  Use "-" only when no machine-verifiable check exists.
  Do not use always-success commands such as "|| true" or "|| echo skip".

DoD:
  Write objective, inspectable outcomes.
  Avoid broad tasks that mix analysis, UI, LLM, CI, and write-back.
-->
