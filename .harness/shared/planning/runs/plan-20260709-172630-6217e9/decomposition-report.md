# Decomposition Report — Sample Repo Validation for Week 8

## 배경

이전 계획(plan-20260709-145543-c46c12)은 Week 8 Task 8.1~8.9를 새로 제안했으나,
그 사이 다른 세션이 같은 문제를 이미 "Week 8 - Evidence-based GitOps Manifest
Planning"으로 계획·구현했다(8.1~8.3 done, 8.4~8.8 todo, commit `f47fa38`).
그 설계가 더 엄격하고(프레임워크 관례 기반 포트 추측을 명시적으로 금지, 근거
기반만 confirmed로 인정) 이미 검증도 더 앞서 있어, 이전 계획은 폐기하고 이번
계획은 그 파이프라인 전체가 실제 샘플 레포 구조에서 올바르게 동작하는지 확인하는
Task 하나만 추가한다.

## Task 목록

### 8.9 — fastapi-template 샘플 레포 기준 dry-run 통합 검증 추가

**완료 기준**: 실제 fastapi/full-stack-fastapi-template의 핵심 파일 구조를 고정
fixture로 박제해서, 파이프라인 전체(8.1~8.7)를 그 fixture에 대해 실행했을 때
아래 4가지가 기대대로 나오는지 검증한다.

1. backend는 Dockerfile에 EXPOSE도 없고 CMD에 `--port` 플래그도 없으므로 포트가
   confirmed되지 않고 manual action으로 남아야 한다 (추측 금지 설계 원칙 확인).
2. frontend는 `nginx.conf`에 실제 `listen 80;`이 있으므로 그 근거로 80이
   confirmed되어야 한다.
3. `config.py`의 pydantic Settings 클래스에서 SECRET_KEY 등은 secret으로,
   POSTGRES_SERVER 등은 public config/configmap으로 정확히 나뉘어야 한다.
4. `compose.yml`의 `image: postgres:18`에서 postgres dependency가 감지돼야 한다.

이 중 하나라도 실패하면 통과할 때까지 8.1~8.7의 해당 analyzer/manifest_plan/
gitops 로직을 고친다 — "검증 pass 못하면 로직 재조정"이라는 요청을 DoD에 그대로
반영했다.

**오프라인 원칙**: 테스트 실행 때마다 실제 GitHub에서 clone하지 않는다. 레포의
핵심 파일(백엔드 Dockerfile/config.py, 프런트 Dockerfile/nginx.conf, compose.yml,
.env)만 `tests/fixtures/fastapi_template/`에 스냅샷으로 복사해두고 그걸로
검증한다. 폐쇄망에서도 항상 같은 결과가 나오고, 실제 레포가 나중에 바뀌어도
테스트가 갑자기 깨지지 않는다.

**확인 방법**: `pytest -q tests/test_fastapi_template_fixture.py`

**먼저 끝나야 할 작업**: 8.7 (파이프라인 전체 — analyzer, manifest_plan,
gitops 렌더러, dashboard/report — 가 완성되어야 end-to-end로 검증할 수 있다).
