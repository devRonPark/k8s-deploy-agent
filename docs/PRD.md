# Operator Console PRD

작성일: 2026-07-06
상태: MVP implemented for local console shell, dry-run execution, generated preview, and Dockerfile proposal artifacts
기준 문서: `docs/ui-ux-plan.md`

## Problem

`k8s-deploy-agent`는 고객사 폐쇄망 또는 on-premise 환경에서 application source repository를 Kubernetes로 이관하기 위한 반복 준비 작업을 자동화한다. 현재 dry-run은 Jenkinsfile, Kaniko build command, Rancher Fleet GitOps manifest, Kubernetes manifest, 분석 리포트, 정적 dashboard를 생성한다.

다음 단계의 local operator console은 이 산출물 생성을 사람이 반복 실행하고 검토하기 쉽게 만드는 로컬 UI다. 목표는 클러스터를 직접 변경하는 자동화가 아니라, 이관 작업자가 입력값을 검증하고 dry-run 산출물을 안전하게 리뷰한 뒤 export 또는 제한된 write-back 준비 단계로 넘어가도록 돕는 것이다.

## Users

- Migration operator: 고객사 현장에서 애플리케이션 이관 dry-run을 실행하고 검증한다.
- Platform engineer: namespace, registry, Jenkins, Rancher Fleet 정책과 산출물 적합성을 검토한다.
- DevOps engineer: source repository 구조, Dockerfile, build/runtime 특성, Jenkinsfile 반영 필요성을 확인한다.

## Goals

- 폐쇄망에서 외부 SaaS, CDN, remote asset 없이 실행되는 local web operator console을 제공한다.
- 기존 `dry-run` command의 deterministic behavior를 유지하면서 UI에서 입력, 실행, 검토를 orchestration한다.
- raw secret 값을 받거나 저장하지 않고 credential ID 또는 token 환경변수 이름만 사용한다.
- 생성된 Jenkinsfile, GitOps/Fleet manifest, Kubernetes manifest, analysis report를 한 화면 흐름에서 검토할 수 있게 한다.
- secret redaction, namespace, image naming, unsupported stack, Dockerfile 누락 같은 validation checklist를 operator가 확인할 수 있게 한다.
- on-prem LLM recommendation은 선택적 review panel에만 표시하고 자동 적용하지 않는다.
- write-back은 validation gate 통과 후 preview/preparation 단계로만 노출한다.

## Non-Goals

- 외부 SaaS LLM 또는 인터넷 기반 API 호출
- raw credential, token, password, kubeconfig, registry secret 값 입력/저장/표시
- UI에서 destructive cluster operation 실행
- LLM recommendation 자동 반영
- multi-user 권한 관리, SSO, audit server
- advanced Helm/Kustomize overlay editor
- production-grade long-running job scheduler

## MVP Scope

### CLI Contract

MVP command:

```bash
k8s-deploy-agent web --host 127.0.0.1 --port 8080
```

기존 command는 유지한다.

```bash
k8s-deploy-agent dry-run --config <config.yaml> --output <dir>
```

`web` command는 local web UI를 시작하고, UI의 dry-run 실행은 기존 dry-run pipeline을 재사용한다.

### Required Inputs

UI는 다음 값을 수집한다.

| Field | Rule |
|-------|------|
| application name | non-empty string |
| environment | operator-defined label |
| target namespace | Kubernetes namespace-compatible value |
| source repository URL | internal repository URL |
| source branch | branch or ref |
| source credential ID | raw secret 금지 |
| source access token env | optional environment variable name only |
| GitOps repository URL | internal GitOps repository URL |
| GitOps branch/path | target branch and path |
| GitOps credential ID | raw secret 금지 |
| private registry URL/project | internal registry target |
| registry credential ID | raw secret 금지 |
| registry CA credential ID | optional credential ID |

### Required Outputs

MVP console은 dry-run 결과에서 다음을 보여준다.

- repository analysis report
- BuildProfile evidence and unresolved questions
- service readiness
- detected stack and Dockerfile status
- review-only Dockerfile and `.dockerignore` proposals when BuildProfile gate passes
- Dockerfile proposal validation report
- generated `Jenkinsfile`
- generated Fleet config
- generated Namespace, Deployment, Service, ConfigMap manifests
- generated image names and tag
- validation checklist result
- export path or write-back preparation summary

## Requirements

| ID | Requirement | Priority | Acceptance |
|----|-------------|----------|------------|
| R1 | `web` command는 local address와 port를 받는다 | Must | `k8s-deploy-agent web --host 127.0.0.1 --port 8080` starts a local server |
| R2 | UI는 `DemoConfig`와 호환되는 config payload를 만든다 | Must | submitted form can run the existing dry-run pipeline |
| R3 | UI는 raw secret field를 제공하지 않는다 | Must | credential inputs are IDs or environment variable names only |
| R4 | dry-run execution은 기존 analyzer, renderer, redaction guard를 재사용한다 | Must | UI dry-run output matches CLI dry-run asset set |
| R5 | generated asset preview는 local files만 읽는다 | Must | no external CDN, font, script, image, or SaaS request is required |
| R6 | validation checklist는 secret redaction failure를 blocking 상태로 표시한다 | Must | detected secret value prevents write-back preparation |
| R7 | LLM integration은 optional on-prem endpoint로 분리한다 | Should | console works when LLM endpoint is unset or unavailable |
| R8 | LLM recommendation은 review-only로 표시한다 | Must | recommendation text does not mutate generated assets |
| R9 | write-back preparation은 validation gate 이후에만 가능하다 | Must | failed checklist disables write-back preparation action |
| R10 | dry-run output remains deterministic for the same config and source tree | Must | repeated run produces the same generated file content except explicit image tag/input changes |
| R11 | Dockerfile proposal은 source repository에 write-back하지 않는다 | Must | proposal files are generated only under `dockerfile-proposals/` |
| R12 | root-level app repository도 service candidate로 감지한다 | Must | root dependency file creates a BuildProfile and eligible proposal artifact |

## Safety Rules

- Secret 원문은 config, generated file, log, UI state, test fixture에 저장하지 않는다.
- Token은 환경변수 이름만 config에 기록한다.
- Redaction guard failure는 operator가 override할 수 없는 blocking validation이다.
- LLM prompt에는 raw secret이 포함되지 않아야 한다.
- LLM output은 generated file에 자동 반영하지 않는다.
- Source repository write-back과 GitOps write-back은 explicit validation gate 뒤의 별도 작업으로 유지한다.

## Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-06 | MVP console은 local web UI로 시작한다 | 폐쇄망 현장에서 브라우저 기반 검토가 쉽고 기존 CLI pipeline을 감싸기 좋다 |
| 2026-07-06 | Existing `dry-run` command remains the core execution path | CLI와 UI 결과 drift를 줄이고 deterministic 검증을 유지한다 |
| 2026-07-06 | LLM은 optional on-prem adapter로만 연결한다 | 외부 SaaS 의존 없이 core generation을 보장한다 |
| 2026-07-06 | UI는 credential ID/env var name만 받는다 | raw secret leakage risk를 줄인다 |
| 2026-07-06 | Dockerfile은 review-only proposal artifact로만 생성한다 | 자동 source write-back 없이 사람이 검토할 수 있는 migration 준비물을 만든다 |

## Open Questions

- Write-back preparation의 첫 지원 대상이 GitOps repository인지 source repository Jenkinsfile인지 결정해야 한다.
- On-prem LLM endpoint protocol은 OpenAI-compatible local endpoint, Ollama-style endpoint, custom HTTP 중 어느 것을 우선할지 결정해야 한다.
