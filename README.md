# k8s-deploy-agent

Kubernetes 배포 자동화 Agent의 Python package root다.

이 Agent는 Source repository를 분석해 Jenkins CI와 Rancher Fleet GitOps CD에 필요한 초기 산출물을 생성한다.
현재 데모 가능한 범위는 dry-run 기반 산출물 생성과 secret redaction 검증이다.

## 핵심 기능

- Source repository file tree 분석
- service 후보와 stack 감지
- service별 Dockerfile 탐지
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
  -> Jenkinsfile 생성
  -> repository analysis report 생성
  -> Rancher Fleet용 GitOps manifest 생성
  -> secret redaction guard 검증
```

상세 시나리오는 `docs/demo-scenario.md`를 참고한다.

## CLI 예시

이 repository를 clone한 뒤 일반 터미널에서 바로 실행할 수 있다.

```bash
uv run k8s-deploy-agent --version
uv run pytest -q
```

dry-run 실행:

```bash
uv run k8s-deploy-agent dry-run \
  --config .agent/config/demo-inputs.example.yaml \
  --repo /path/to/source-repo \
  --output ./out/demo
```

`/path/to/source-repo`에는 분석 대상 애플리케이션 repository 경로를 넣는다.
예상 구조는 `backend/Dockerfile`, `frontend/Dockerfile`처럼 service별 Dockerfile이 있는 repository다.

생성 결과:

```text
out/demo/.agent/reports/repository-analysis.md
out/demo/Jenkinsfile
out/demo/gitops/fleet.yaml
out/demo/gitops/base/namespace.yaml
out/demo/gitops/apps/<service>/deployment.yaml
out/demo/gitops/apps/<service>/service.yaml
out/demo/gitops/apps/<service>/configmap.yaml
```

## Demo 입력 파일

기본 예시는 `.agent/config/demo-inputs.example.yaml`에 있다.

Secret 값은 입력하지 않는다. Jenkins credential ID만 config에 넣는다.

```yaml
source_credential_id: "gitea-source-credential"
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
- Dockerfile 자동 생성
- Helm/Kustomize 고급 overlay 생성
- 외부 SaaS LLM 호출
