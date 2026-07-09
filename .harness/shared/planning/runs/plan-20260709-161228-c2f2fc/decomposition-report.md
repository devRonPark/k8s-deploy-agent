# Decomposition Report

## 요청

`Introduce evidence-based WorkloadManifestPlan for dry-run GitOps generation`

## 분해 기준

첨부 요청은 하나의 큰 구현으로 보이지만 실제로는 service discovery, port analysis,
env/dependency analysis, manifest plan builder, GitOps rendering, report/dashboard,
documentation이 서로 다른 관심사다. 각 Task는 독립적으로 테스트할 수 있는 interface를
하나씩 노출하도록 나눴다.

## 제안 Task

### 8.1 monorepo workspace service discovery 개선

완료 기준은 analyzer가 root-level app과 일반 디렉터리 구조를 유지하면서
`apps/*`, `services/*`, `packages/*` workspace service를 감지하는 것이다.
확인은 `tests/test_build_profile.py`의 monorepo 관련 테스트로 한다.

### 8.2 evidence 기반 port analyzer 추가

완료 기준은 `PortCandidate`와 port analyzer가 Dockerfile, compose, nginx,
runtime/config evidence를 분리해 수집하는 것이다. 이 단계는 YAML을 렌더링하지
않고 분석 결과만 검증한다.

### 8.3 env var와 dependency analyzer 추가

완료 기준은 env key만 수집하고 raw value를 출력하지 않으며, secret/public config와
stateful/external dependency 후보를 분류하는 것이다. Secret-like 판정은
`redaction.py`의 public helper로 재사용한다.

### 8.4 WorkloadManifestPlan builder 추가

완료 기준은 port/env/dependency 분석과 BuildProfile을 묶어 service별
`confirmed`와 `unresolved_questions`를 결정하는 것이다. Dockerfile proposal은
review-only artifact이므로 confirmed 근거가 될 수 없다는 규칙을 여기에 둔다.

### 8.5 GitOps renderer를 WorkloadManifestPlan 기반으로 전환

완료 기준은 `gitops.py`가 분석하지 않고 plan만 렌더링하는 것이다. confirmed
container port가 없으면 Deployment/Service를 생성하지 않고, ConfigMap은 분석된
ConfigMap key 기준으로만 생성한다.

### 8.6 dry-run manual-actions.md report 추가

완료 기준은 skipped manifests, unresolved/conflicting ports, secret keys,
dependencies, external exposure, image tag 차이를 operator가 볼 수 있는
`.agent/reports/manual-actions.md`에 남기는 것이다.

### 8.7 report와 dashboard를 manifest plan readiness로 전환

완료 기준은 repository analysis report와 dashboard가 Dockerfile 존재 여부가 아니라
`WorkloadManifestPlan.confirmed`를 readiness 기준으로 사용하고, plan evidence를
표시하는 것이다.

### 8.8 README dry-run manifest analysis 원칙 업데이트

완료 기준은 사용자가 dry-run GitOps 생성의 보수적 원칙과 금지 사항을 README에서
확인할 수 있는 것이다.

## 범위 제외

요청의 금지 사항에 따라 Ingress, DB/Redis manifest, Helm, Kustomize, Fleet GitRepo
등록, Jenkins pipeline 대규모 변경, source/GitOps write-back, LLM adapter, 외부
repository clone/fetch 기반 테스트는 Task로 만들지 않았다.
