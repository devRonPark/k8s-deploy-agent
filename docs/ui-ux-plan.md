# UI/UX Plan - k8s-deploy-agent

작성일: 2026-07-06
상태: Phase 1-2 implemented, Phase 3-4 planned
전제: 폐쇄망 local execution, existing dry-run pipeline reuse

## 1. 목적

이 Agent는 고객사 폐쇄망 환경에서 application source code repository를 Kubernetes cluster로 이관하기 위한 반복 작업을 자동화한다.

고객사로부터 source repository 계정과 접근 권한을 받은 뒤, Agent가 repository를 분석하고 Jenkins CI, container image build, private registry, Rancher Fleet GitOps, Kubernetes manifest, 검증 리포트 생성을 지원한다.

UI/UX의 목적은 단순 산출물 보기보다, 이관 작업자가 폐쇄망 현장에서 동일한 절차를 안정적으로 수행할 수 있는 operator console을 제공하는 것이다.

## 2. 운영 환경

- 고객사 폐쇄망 내부에서 실행한다.
- 외부 SaaS LLM 호출을 전제로 하지 않는다.
- Dell Pro Max GB10 장비 1대를 현장에 반입한다.
- 해당 장비에서 on-premise LLM model을 구동한다.
- Agent는 로컬 또는 내부망 endpoint로 on-prem LLM과 연동한다.
- source repository, GitOps repository, registry, Jenkins, Rancher/Fleet은 고객사 내부 시스템을 사용한다.

## 3. UX 방향

최종 UI는 dry-run 결과 viewer가 아니라 Kubernetes 이관 작업을 단계별로 진행하는 operator console이어야 한다.

권장 흐름:

```text
Project Onboarding
  -> Source Repository Access
  -> Repository Analysis
  -> LLM-assisted Review
  -> Generated Asset Preview
  -> Validation Checklist
  -> Export / Write-back Preparation
```

## 4. 주요 화면

### 4.1 Project Onboarding

작업자가 이관 대상 application 정보를 입력한다.

- application name
- environment
- target namespace
- source repository URL
- source branch
- source credential ID
- GitOps repository URL
- GitOps branch/path
- GitOps credential ID
- private registry URL/project
- registry credential ID
- registry CA credential ID

Secret 값은 UI에 직접 입력하지 않는다.
UI는 credential ID 또는 token 환경변수 이름만 받는다.

### 4.2 Repository Analysis

source repository 분석 결과를 보여준다.

- file tree summary
- service 후보 목록
- stack 감지 결과
- Dockerfile 존재 여부
- BuildProfile evidence와 confidence
- Dockerfile proposal validation 상태
- build context
- unsupported stack 여부
- Kubernetes 이관 위험 요소

### 4.3 LLM-assisted Review

on-prem LLM을 사용해 분석 결과를 보조한다.

예상 질의:

- 이 repository의 application 구조 요약
- service별 build/runtime 특성
- Dockerfile이 없는 service의 처리 방향
- Kubernetes manifest 생성 시 주의점
- Jenkins pipeline 누락 가능성
- registry, secret, config 처리 위험

LLM 응답은 자동 적용하지 않고, 작업자가 검토할 수 있는 recommendation으로 표시한다.

### 4.4 Generated Asset Preview

Agent가 생성한 산출물을 UI에서 확인한다.

- repository analysis report
- Jenkinsfile
- Fleet config
- namespace manifest
- Deployment
- Service
- ConfigMap
- Dockerfile proposal
- `.dockerignore` proposal
- Dockerfile proposal validation report

현재 구현은 preview 중심으로 둔다.
이후 필요하면 제한된 field override를 추가한다.

### 4.5 Validation Checklist

생성 산출물과 입력값을 검증한다.

- secret value가 산출물에 포함되지 않았는지
- credential ID만 사용했는지
- namespace 규칙이 맞는지
- image naming 규칙이 registry 정책과 맞는지
- unsupported service가 남아있는지
- Dockerfile 누락 service가 있는지
- GitOps path가 올바른지
- 생성된 manifest가 service별로 완비되었는지

### 4.6 Export / Write-back Preparation

harness 적용 이후 실제 write-back 방식에 맞춰 확장한다.

후보 기능:

- dry-run output export
- GitOps repository commit 준비
- source repository Jenkinsfile write-back 준비
- 변경 파일 diff preview
- 작업 로그 export
- 검증 리포트 export

## 5. 구현 방향

초기 UI는 로컬 실행형 웹 UI로 구현한다.

예상 명령:

```bash
uv run k8s-deploy-agent web --host 127.0.0.1 --port 8080
```

현재 구현 원칙:

- 폐쇄망 실행을 우선한다.
- 외부 CDN, 외부 font, 외부 JS dependency를 사용하지 않는다.
- 기존 dry-run CLI는 유지한다.
- UI는 CLI 기능을 감싸는 얇은 orchestration layer로 시작한다.
- Dockerfile proposal은 review-only artifact로만 표시한다.
- LLM 연동은 provider abstraction을 둔다.

## 6. On-prem LLM 연동 계획

LLM 연동은 Agent core와 분리한다.

초기 abstraction:

```text
Agent analysis result
  -> prompt builder
  -> local LLM endpoint
  -> structured recommendation
  -> UI review panel
```

LLM 사용 범위:

- repository 구조 설명
- migration risk 요약
- Dockerfile/manifest 개선 제안
- Jenkins pipeline 검토
- operator checklist 생성

LLM 비사용 범위:

- secret 값 생성 또는 저장
- credential 원문 처리
- 검증 없이 산출물 자동 적용
- cluster destructive operation 자동 실행

## 7. 단계별 로드맵

### Phase 1 - Static Result Dashboard

현재 dry-run output에 `index.html`을 생성해 결과를 빠르게 확인한다.

범위:

- service readiness
- generated assets
- image tag
- namespace
- file scan summary
- Dockerfile proposal validation

### Phase 2 - Local Operator Console

현재 구현된 local console 범위다.

범위:

- `web` command 추가
- config 입력 form
- dry-run 실행 button
- 분석 결과 화면
- 생성 산출물 preview
- validation checklist
- Dockerfile proposal validation preview

### Phase 3 - On-prem LLM Review

범위:

- local LLM endpoint 설정
- repository analysis prompt
- recommendation panel
- manifest/Jenkinsfile review prompt
- operator checklist 자동 생성

### Phase 4 - Controlled Write-back

범위:

- GitOps repository 변경 preview
- source repository 변경 preview
- commit message 생성 보조
- write-back 전 validation gate
- 작업 로그와 리포트 export

## 8. 현재 구현하지 않을 것

- 외부 SaaS LLM 연동
- credential secret 값 저장
- UI에서 destructive cluster operation 실행
- LLM recommendation 자동 적용
- 복잡한 multi-user 권한 관리
- Dockerfile/source repository 자동 write-back
