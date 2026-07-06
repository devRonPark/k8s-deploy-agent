# Demo Scenario — k8s-deploy-agent

작성일: 2026-07-06
대상: 플랫폼/DevOps 엔지니어

이 문서는 현재 package root 기준으로 구성된 Agent가 시연할 수 있는 1차 Demo 흐름을 설명한다.

## 1. Demo 목표

기존 애플리케이션 repository를 입력하면 Agent가 배포 자동화에 필요한 초기 산출물을 생성한다.

```text
Source repository
  -> Agent repository 분석
  -> service 및 Dockerfile 탐지
  -> Jenkinsfile 생성
  -> repository analysis report 생성
  -> Rancher Fleet용 GitOps manifest 생성
  -> secret redaction guard 검증
```

## 2. 등장 Agent 역할

| 역할 | 시연 포인트 |
| --- | --- |
| Advisor | PRD와 MVP 범위를 기준으로 dry-run 산출물 생성 범위를 고정한다. |
| Worker | repository를 분석하고 Jenkinsfile, 분석 리포트, GitOps manifest를 생성한다. |
| Test Agent | acceptance/test 명령으로 산출물 생성을 검증한다. |
| Reviewer | secret 노출, Jenkinsfile stage, GitOps 구조, 회귀 위험을 점검한다. |

## 3. Demo 입력

입력 config는 flat YAML 또는 `.env` 형태의 key/value를 사용한다.

주요 입력값:

| 항목 | 설명 |
| --- | --- |
| `source_repo_url` | 분석 대상 Source repository URL |
| `source_branch` | Source branch |
| `source_credential_id` | Jenkins Source repository credential ID |
| `gitops_repo_url` | GitOps repository URL |
| `gitops_credential_id` | Jenkins GitOps repository credential ID |
| `app_name` | 애플리케이션 이름 |
| `environment` | 배포 환경 이름 |
| `registry_url` | SUSE Private Registry URL |
| `registry_project` | Registry project 이름 |
| `registry_credential_id` | Registry push credential ID |
| `registry_ca_cert_credential_id` | Self-signed CA secret file credential ID |

Secret 값은 config에 직접 넣지 않는다. Agent와 Jenkinsfile은 credential ID만 사용한다.

## 4. Demo 대상 Repository

권장 시연 대상은 `fastapi/full-stack-fastapi-template`을 사내 Gitea로 import한 private repository다.

감지되어야 하는 service:

| Service | Path | Stack | Dockerfile |
| --- | --- | --- | --- |
| `backend` | `backend/` | Python/FastAPI | `backend/Dockerfile` |
| `frontend` | `frontend/` | Node.js/React/Vite | `frontend/Dockerfile` |

현재 Agent는 directory root의 대표 파일로 service를 감지한다.

| 파일 | 감지 stack |
| --- | --- |
| `package.json` | `node` |
| `pyproject.toml`, `requirements.txt` | `python` |
| `pom.xml`, `build.gradle` | `java` |
| `go.mod` | `unsupported` |

`unsupported` stack이거나 Dockerfile이 없는 service는 Jenkinsfile/GitOps manifest 생성 대상에서 제외한다.

## 5. 시연 절차

### 5.1 dry-run 실행

이 명령은 Claude Code나 Codex CLI가 아니라 일반 터미널에서 실행할 수 있다.

```bash
uv run k8s-deploy-agent dry-run \
  --config .agent/config/demo-inputs.example.yaml \
  --repo /path/to/fastapi-demo-source \
  --output ./out/demo
```

기대 출력:

```text
dry-run complete: 10 files written to ./out/demo
```

### 5.2 생성 파일 확인

```bash
find ./out/demo -type f | sort
```

기대 산출물:

```text
out/demo/.agent/reports/repository-analysis.md
out/demo/Jenkinsfile
out/demo/gitops/fleet.yaml
out/demo/gitops/base/namespace.yaml
out/demo/gitops/apps/backend/configmap.yaml
out/demo/gitops/apps/backend/deployment.yaml
out/demo/gitops/apps/backend/service.yaml
out/demo/gitops/apps/frontend/configmap.yaml
out/demo/gitops/apps/frontend/deployment.yaml
out/demo/gitops/apps/frontend/service.yaml
```

### 5.3 분석 리포트 확인

```bash
cat ./out/demo/.agent/reports/repository-analysis.md
```

검증 포인트:

- `backend`와 `frontend` service가 표시된다.
- 각 service의 stack과 Dockerfile 경로가 표시된다.
- Secret 값이 포함되지 않는다.

### 5.4 Jenkinsfile 확인

```bash
sed -n '1,220p' ./out/demo/Jenkinsfile
```

검증 포인트:

- Jenkins Kubernetes Plugin `podTemplate`을 사용한다.
- Kaniko container로 service별 image를 build/push한다.
- Registry username/password credential과 CA secret file credential을 binding한다.
- GitOps repository를 clone하고 manifest를 생성한 뒤 commit/push한다.

Image naming 규칙:

```text
<REGISTRY_URL>/<REGISTRY_PROJECT>/<APP_NAME>-<SERVICE_NAME>:${BUILD_NUMBER}
```

## 6. 성공 기준

Demo 성공 기준:

- `dry-run`이 성공한다.
- 분석 리포트에 service와 Dockerfile 경로가 표시된다.
- Jenkinsfile에 `Checkout Source`, `Build and Push Images`, `Update GitOps Repository` 흐름이 포함된다.
- GitOps manifest가 service별로 생성된다.
- 산출물에 secret 값이 포함되지 않는다.
- 관련 pytest가 통과한다.

## 7. 현재 Demo 범위 밖

- Gitea webhook 자동 trigger
- Rancher Fleet `GitRepo` 자동 등록
- 실제 cluster rollout 검증
- Dockerfile 자동 생성
- Helm/Kustomize 고급 overlay 생성
- 외부 SaaS LLM 호출
