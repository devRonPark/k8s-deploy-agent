# k8s-deploy-agent Workflow Overview

작성일: 2026-07-06
대상: Kubernetes 기반 애플리케이션 배포 워크플로우를 이해하는 의사결정자
상태: current implemented workflow

## 한 줄 요약

`k8s-deploy-agent`는 고객사 on-premise 또는 폐쇄망 환경에서 application source repository를 분석하고, Kubernetes 배포 준비에 필요한 CI/CD, GitOps, manifest, Dockerfile proposal, validation 산출물을 dry-run 방식으로 생성하는 로컬 실행형 에이전트다.

## 현재 에이전트가 하는 일

```text
Source repository + migration config
  -> repository clone or local path scan
  -> service and stack detection
  -> BuildProfile evidence generation
  -> Dockerfile/.dockerignore proposal preview
  -> Jenkins + Kaniko pipeline generation
  -> Rancher Fleet GitOps manifest generation
  -> Kubernetes Namespace/Deployment/Service/ConfigMap generation
  -> secret redaction and validation checks
  -> local dashboard / operator console preview
```

이 흐름은 실제 cluster 변경이나 source repository write-back을 수행하지 않는다. 현재 구현은 운영자가 검토할 수 있는 안전한 dry-run 산출물을 만드는 단계다.

## 입력

에이전트는 다음 정보를 받는다.

| 입력 | 용도 |
|------|------|
| source repository URL 또는 local path | 분석할 애플리케이션 소스 |
| source branch/ref | 분석 대상 revision |
| source credential ID 또는 token env var name | private repository 접근 참조 |
| application name, environment, namespace | Kubernetes naming과 report 기준 |
| GitOps repository URL/branch/path | Fleet 산출물 배치 대상 정보 |
| registry URL/project | image destination 계산 |
| registry credential ID, CA credential ID | Jenkins credential binding 참조 |

Secret 원문은 config, UI, generated file, log, test fixture에 저장하지 않는다. Token은 값이 아니라 환경변수 이름으로만 전달한다.

## 분석 단계

에이전트는 repository를 스캔해 service candidate를 만든다.

| 감지 기준 | Stack |
|-----------|-------|
| `package.json` | Node.js |
| `pyproject.toml`, `requirements.txt` | Python |
| `pom.xml`, `build.gradle` | Java |
| `go.mod` | Go |

지원 repository shape:

- `backend/`, `frontend/`처럼 하위 directory에 service별 manifest가 있는 multi-service repository
- repository root에 manifest가 있는 single-service repository

각 service에는 `BuildProfile`이 생성된다. 여기에는 build tool, dependency file, lockfile, runtime command, build output, Dockerfile 존재 여부, exposed port, confidence, evidence, unresolved question이 포함된다.

## Dockerfile Proposal

현재 Dockerfile은 source repository에 자동 반영하지 않는다. 대신 검토용 proposal artifact만 생성한다.

```text
dockerfile-proposals/VALIDATION.md
dockerfile-proposals/<service>/Dockerfile
dockerfile-proposals/<service>/.dockerignore
```

Proposal은 다음 gate를 통과해야 생성된다.

- supported stack: Python, Node.js, Java, Go
- service path 확정
- dependency file과 build tool 확정
- runtime command 확정
- exposed port 확정
- unresolved question 없음
- secret-like 값 없음

`VALIDATION.md`는 secret redaction, review-only output path, BuildProfile confidence gate를 확인한다.

## 생성 산출물

Dry-run output은 운영자가 바로 검토할 수 있는 파일 구조로 생성된다.

| 산출물 | 목적 |
|--------|------|
| `.agent/reports/repository-analysis.md` | service, stack, Dockerfile, BuildProfile evidence 요약 |
| `Jenkinsfile` | Jenkins Kubernetes Plugin 기반 CI pipeline 초안 |
| Kaniko command | service별 image build/push command |
| `gitops/fleet.yaml` | Rancher Fleet bundle 설정 |
| `gitops/base/namespace.yaml` | target namespace manifest |
| `gitops/apps/<service>/deployment.yaml` | service별 Deployment |
| `gitops/apps/<service>/service.yaml` | service별 Service |
| `gitops/apps/<service>/configmap.yaml` | service별 ConfigMap |
| `dockerfile-proposals/` | review-only Dockerfile/`.dockerignore` proposal |
| `index.html` | dry-run 결과를 보는 static dashboard |

## 실행 방식

CLI dry-run:

```bash
k8s-deploy-agent dry-run \
  --config .agent/config/demo-inputs.example.yaml \
  --output ./out/demo
```

Local operator console:

```bash
k8s-deploy-agent web --host 127.0.0.1 --port 8080
```

Console은 외부 CDN, font, JavaScript, SaaS API 없이 로컬에서 동작한다. Form validation, dry-run 실행, generated asset preview, validation checklist를 같은 브라우저 흐름에서 제공한다.

## 안전장치

| Gate | 동작 |
|------|------|
| Config validation | namespace, required field, credential reference 형식 확인 |
| Secret redaction | generated asset에 secret-like 값이 있으면 실패 |
| BuildProfile confidence gate | 불확실한 Dockerfile proposal 생성 차단 |
| Review-only output | Dockerfile proposal은 output directory에만 생성 |
| Write-back boundary | source/GitOps repository push는 현재 구현 범위 밖 |
| Offline boundary | 외부 SaaS, CDN, remote asset 의존 없음 |

## 운영자가 보는 판단 포인트

이 에이전트의 현재 가치는 자동 배포가 아니라 migration preparation을 빠르게 표준화하는 데 있다.

- 이 repository에서 Kubernetes 배포 대상 service가 무엇인지
- 어떤 service가 Jenkins/GitOps manifest 생성 대상인지
- Dockerfile이 이미 있는지, 없으면 어떤 proposal이 가능한지
- image name, namespace, manifest path가 내부 표준과 맞는지
- raw secret이 산출물에 섞이지 않았는지
- write-back 전에 사람이 검토해야 할 unresolved question이 무엇인지

## 현재 범위 밖

- 실제 Kubernetes cluster rollout
- Rancher Fleet `GitRepo` 자동 등록
- source repository 또는 GitOps repository 자동 push
- Dockerfile 자동 적용
- Docker build 실행
- base image vulnerability scan
- 외부 SaaS LLM 호출
- multi-user 권한 관리

## 현재 상태

현재 구현은 local dry-run과 local operator console 중심의 검토 가능한 workflow다. 다음 단계는 on-prem LLM recommendation panel과 validation gate 이후의 controlled write-back preparation을 별도 task로 확장하는 것이다.
