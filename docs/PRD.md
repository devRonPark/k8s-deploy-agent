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

UI는 초기 분석 테스트와 실제 GitOps/write-back 준비를 구분해 값을 수집한다.

초기 분석 테스트는 다음 값만으로 실행 가능해야 한다.

| Field | Rule |
|-------|------|
| application name | non-empty string |
| environment | operator-defined label |
| target namespace | Kubernetes namespace-compatible value |
| source repository URL 또는 local source repository path | internal repository URL or server local path |
| source branch | branch or ref; local mode는 `local` placeholder 사용 |
| source credential ID | private source repository일 때 raw secret이 아닌 credential ID. clone 모드에서 비워두면 anonymous clone을 기본 동작으로 시도한다 |
| source access token env | optional environment variable name only |

GitOps target을 비워 둔 초기 분석 테스트는 review-only placeholder GitOps config를 사용해 local dry-run artifact만 생성한다. 이 placeholder는 generated Jenkinsfile과 manifest preview를 만들기 위한 값이며 source/GitOps repository에 push하지 않는다.

Source credential ID가 비어 있는 clone 모드는 특정 URL에 대한 예외 처리가 아니라 일반 규칙으로 anonymous clone을 시도한다. 대상 repository가 실제로 public이면 검증 -> dry-run이 정상 완료되고, 실제로는 private repository인데 credential이 없으면 dry-run 단계에서 git 인증 실패로 명확히 실패하며 "private repository면 source credential ID를 입력하세요" 안내 문구를 함께 보여준다.

GitOps/write-back 준비 단계는 다음 값을 추가로 요구한다.

| Field | Rule |
|-------|------|
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
| R13 | operator console은 작업 대상과 Source repository 입력만으로 초기 분석 테스트를 실행한다 | Must | GitOps target 입력이 모두 비어 있어도 validation과 local dry-run이 review-only placeholder GitOps config로 통과한다 |
| R14 | clone 모드에서 source_credential_id가 비어 있으면 특정 URL 예외 없이 anonymous clone을 기본 동작으로 시도한다 | Must | 임의의 public repository URL(하드코딩된 데모 URL이 아니어도)과 branch만 입력하면 validation과 dry-run이 통과한다. 대상이 실제 private repository면 dry-run이 git 인증 실패 메시지와 함께 "private repository면 source credential ID를 입력하세요" 안내 문구를 보여주며 명확히 실패한다 |

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
| 2026-07-09 | operator console 초기 분석 테스트는 GitOps target 없이 실행 가능하게 한다 | 작업 대상과 Source repository만 확보된 상태에서 1차 repository 분석과 generated asset preview를 확인할 수 있어야 한다 |
| 2026-07-09 | clone 모드에서 source_credential_id가 비어 있으면 특정 하드코딩 URL이 아니라 일반 규칙으로 anonymous clone을 시도한다 | 기존에는 `_is_public_sample_clone`이 FastAPI 데모 URL/branch 조합에만 credential 없이 통과시켰고, 다른 public repository URL은 동일한 상황에서도 `Missing required config fields: source_credential_id`로 거부되는 버그가 있었다. GitOps target에 이미 적용된 placeholder 기본값 패턴과 일관되게 맞춘다 |
| 2026-07-09 | 하드코딩된 FastAPI 데모 URL 전용 예외 함수(`_is_public_sample_clone`)는 제거하고 일반 anonymous clone 판정(`_is_anonymous_clone`)으로 통합한다. `PUBLIC_SAMPLE_REPO_URL`/`PUBLIC_SAMPLE_BRANCH` 상수는 sample 값 채우기 버튼에서 계속 쓰이므로 유지한다 | 특정 URL만 예외로 인정하는 검증 로직은 유지보수 부채이며, 사용자가 다른 public repository를 입력할 때마다 같은 버그를 재현시킨다. sample 버튼은 검증 로직과 무관한 별개 UI 편의 기능이라 남겨둔다 |
| 2026-07-09 | anonymous clone이 git 인증 실패로 끝나면 dry-run 에러 메시지에 "private repository면 source credential ID를 입력하세요" 안내 문구를 추가한다 | sanitized git stderr만으로는 실패 원인이 credential 누락인지 파악하기 어려워 operator가 헤맬 수 있다 |

## Open Questions

- Write-back preparation의 첫 지원 대상이 GitOps repository인지 source repository Jenkinsfile인지 결정해야 한다.
- On-prem LLM endpoint protocol은 OpenAI-compatible local endpoint, Ollama-style endpoint, custom HTTP 중 어느 것을 우선할지 결정해야 한다.
