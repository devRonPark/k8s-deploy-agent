# k8s-deploy-agent

Kubernetes 배포 자동화 Agent의 Python package root다.

이 Agent는 Source repository를 분석해 Jenkins CI와 Rancher Fleet GitOps CD에 필요한 초기 산출물을 생성한다.
현재 데모 가능한 범위는 dry-run 기반 산출물 생성, secret redaction 검증, review-only Dockerfile proposal 생성이다.

## 핵심 기능

- Source repository file tree 분석
- service 후보와 stack 감지
- service별 Dockerfile 탐지
- service별 BuildProfile evidence 생성
- Python/Node.js/Java/Go Dockerfile proposal preview 생성
- `.dockerignore` proposal preview 생성
- Jenkins Kubernetes Plugin 기반 `Jenkinsfile` 생성
- Kaniko image build/push command 생성
- SUSE Private Registry credential/CA binding 생성
- Rancher Fleet용 GitOps manifest 생성
- repository analysis report 생성
- 생성 산출물 secret redaction guard 검증

## 주요 모듈

| 파일 | 역할 |
| --- | --- |
| `cli.py` | `k8s-deploy-agent dry-run` CLI 진입점 |
| `config.py` | Demo 입력 config parsing 및 validation |
| `analyzer.py` | repository file tree, service, stack, Dockerfile 감지 |
| `build_profile.py` | Dockerfile proposal 전 단계 BuildProfile 모델 |
| `dockerfile_gate.py` | low-confidence/unresolved profile proposal 차단 |
| `dockerfile_proposal.py` | review-only Dockerfile/`.dockerignore` proposal 생성 |
| `dockerfile_validation.py` | Dockerfile proposal validation report 생성 |
| `jenkinsfile.py` | Jenkinsfile 생성 |
| `gitops.py` | Fleet/Kubernetes manifest 생성 |
| `report.py` | repository analysis report 생성 |
| `redaction.py` | 생성 산출물 secret value 탐지 |
| `git_adapter.py` | Source repository write-back 대상 제한 |

## Demo 흐름

```text
Source repository
  -> Agent repository 분석
  -> service 및 Dockerfile 탐지
  -> BuildProfile evidence 생성
  -> Dockerfile/.dockerignore proposal preview 생성
  -> Jenkinsfile 생성
  -> repository analysis report 생성
  -> Rancher Fleet용 GitOps manifest 생성
  -> secret redaction guard 검증
```

상세 시나리오는 `docs/demo-scenario.md`를 참고한다.

## CLI 예시

이 repository를 clone한 뒤 일반 터미널에서 바로 실행할 수 있다.

uv가 없다면 먼저 설치한다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
```

이 repository는 `uv.toml`에서 cache를 `.uv-cache/`로 고정해, home cache 권한에 의존하지 않고 `uv run`으로 실행된다.

```bash
uv run k8s-deploy-agent --version
uv run pytest -q
```

dry-run 실행:

```bash
uv run k8s-deploy-agent dry-run \
  --config .agent/config/demo-inputs.example.yaml \
  --output ./out/demo
```

local operator console 실행:

```bash
uv run k8s-deploy-agent web --host 127.0.0.1 --port 8080
```

현재 console은 외부 CDN, 외부 font, 외부 JS 없이 로컬 HTML shell을 제공한다.
Project onboarding form submit은 `DemoConfig` compatible payload를 검증하고 raw secret-like 값을 차단한다.
`Run dry-run` 버튼은 기존 dry-run pipeline을 호출해 로컬 output directory에 산출물을 생성한다.

기본 실행은 config의 `source_repo_url`, `source_branch`, `source_credential_id`로 source repository를 임시 clone한 뒤 분석한다.
private source repository를 clone해야 하면 config의 `source_access_token_env`에 환경변수 이름을 넣고, 해당 환경변수에 access token을 설정한다.
이미 로컬에 clone된 repository를 분석하려면 `--repo /path/to/source-repo`를 추가한다.
예상 source 구조는 `backend/Dockerfile`, `frontend/Dockerfile`처럼 service별 Dockerfile이 있는 repository다.

생성 결과:

```text
out/demo/index.html
out/demo/.agent/reports/repository-analysis.md
out/demo/Jenkinsfile
out/demo/dockerfile-proposals/VALIDATION.md
out/demo/dockerfile-proposals/<service>/Dockerfile
out/demo/dockerfile-proposals/<service>/.dockerignore
out/demo/gitops/fleet.yaml
out/demo/gitops/base/namespace.yaml
out/demo/gitops/apps/<service>/deployment.yaml
out/demo/gitops/apps/<service>/service.yaml
out/demo/gitops/apps/<service>/configmap.yaml
```

`index.html`은 dry-run 결과를 서비스 준비 상태, 생성 산출물, image tag, Dockerfile proposal validation 기준으로 확인하는 정적 UI다.

월간 회의용 데모 흐름은 `docs/monthly-demo.md`를 참고한다.

## Demo 입력 파일

기본 예시는 `.agent/config/demo-inputs.example.yaml`에 있다.

Secret 값은 입력하지 않는다. Jenkins credential ID만 config에 넣는다.

```yaml
source_credential_id: "gitea-source-credential"
source_access_token_env: "K8S_DEPLOY_AGENT_SOURCE_TOKEN"
gitops_credential_id: "gitea-gitops-credential"
registry_credential_id: "suse-registry-credential"
registry_ca_cert_credential_id: "suse-registry-ca-cert"
```

## 검증

```bash
uv run pytest -q
```

## 현재 Demo 범위 밖

- Gitea webhook 자동 trigger
- Rancher Fleet `GitRepo` 자동 등록
- 실제 cluster rollout 검증
- Dockerfile/source repository 자동 write-back
- Docker build 실행
- Helm/Kustomize 고급 overlay 생성
- 외부 SaaS LLM 호출
