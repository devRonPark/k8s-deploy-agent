# Monthly Demo Runbook

작성일: 2026-07-06
대상: 팀 월간 회의
상태: current demo-ready scope

## 한 줄 요약

`k8s-deploy-agent`는 폐쇄망에서 실행되는 local operator console과 기존 `dry-run` 파이프라인을 결합해, source repository 분석부터 generated asset review, validation checklist 확인까지 한 흐름으로 보여준다.

## 회의에서 보여줄 범위

- `k8s-deploy-agent web --host 127.0.0.1 --port 8080`
- Project onboarding form validation
- `Run dry-run` 버튼으로 existing dry-run pipeline 실행
- Generated asset preview
- Validation checklist
- Dockerfile proposal validation

## 데모 순서

### 1. 콘솔 시작

```bash
uv run k8s-deploy-agent web --host 127.0.0.1 --port 8080
```

기대 상태:

- local loopback에서만 동작한다
- 외부 CDN, 외부 font, 외부 JS를 사용하지 않는다
- raw secret input은 받지 않는다

### 2. 입력 검증

Project onboarding form에 다음 값을 넣는다.

- application name
- environment
- target namespace
- source repository URL
- source branch
- source credential ID
- source access token env
- GitOps repository URL
- GitOps branch/path
- GitOps credential ID
- registry URL/project
- registry credential ID
- registry CA credential ID

검증 포인트:

- credential ID 또는 environment variable name만 허용한다
- raw secret-like 값은 차단된다
- `source_access_token_env`는 uppercase environment variable name이어야 한다

### 3. Dry-run 실행

`Run dry-run`을 누르면 console이 기존 CLI dry-run 코어를 재사용한다.

기대 결과:

- source repository clone
- repository analysis
- BuildProfile evidence generation
- Dockerfile/.dockerignore proposal preview generation
- Jenkinsfile generation
- Fleet/Kubernetes manifest generation
- secret redaction guard execution
- local output directory write

### 4. Generated asset preview

preview 패널에서 다음 파일을 본다.

- `.agent/reports/repository-analysis.md`
- `Jenkinsfile`
- `gitops/fleet.yaml`
- `gitops/base/namespace.yaml`

검증 포인트:

- service 후보와 Dockerfile 경로가 보인다
- BuildProfile evidence와 confidence가 보인다
- Jenkinsfile이 생성된다
- namespace manifest가 target namespace와 맞는다
- Dockerfile proposal validation report가 보인다

### 5. Validation checklist

체크리스트에서 다음을 확인한다.

- secret redaction
- generated assets
- namespace alignment
- Dockerfile proposals
- on-prem LLM is review-only

## 성공 기준

- web console이 열린다
- validation이 동작한다
- dry-run이 output directory를 만든다
- preview가 local generated files를 보여준다
- checklist가 blocking 상태와 pass 상태를 구분한다
- Dockerfile proposal이 source repository write-back 없이 `dockerfile-proposals/` 아래 생성된다
- pytest가 통과한다

## 현재 한계

- 실제 source/GitOps write-back은 아직 없다
- LLM review panel은 아직 통합되지 않았다
- preview는 local output file 기반의 정적 preview다
- 권한 관리와 multi-user workflow는 없다
- Dockerfile은 source repository에 자동 적용하지 않고 `dockerfile-proposals/` review artifact로만 생성된다

## 회의용 메시지

이 구현은 운영 버전이 아니라, 폐쇄망 migration 작업자가 반복 가능한 검증 흐름을 확보하기 위한 데모 가능한 operator console의 첫 단계다.
