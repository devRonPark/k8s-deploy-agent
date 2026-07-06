# Operator Console Architecture

작성일: 2026-07-06
상태: MVP implemented for local console and Dockerfile proposal preview
기준 문서: `docs/ui-ux-plan.md`, `docs/PRD.md`, `docs/UserFlow.md`

## Context

`k8s-deploy-agent`는 고객사 폐쇄망 또는 on-premise 환경에서 실행된다. Core value는 source repository를 분석하고 Kubernetes 이관 준비 산출물을 deterministic하게 생성하는 것이다.

Operator console은 core generation을 대체하지 않는다. Console은 local web UI와 thin orchestration layer로 시작하며, 기존 dry-run pipeline을 재사용해 입력, 실행, preview, validation, export/write-back preparation 흐름을 제공한다.

## Component Model

```text
CLI
  -> dry-run command
  -> web command

Local Web UI
  -> config input form
  -> dry-run execution controller
  -> analysis result view
  -> generated asset preview
  -> validation checklist
  -> optional LLM recommendation panel
  -> export / write-back preparation view

Core Pipeline
  -> Config Loader / Validator
  -> Source Repository Adapter
  -> Repository Analyzer
  -> Build Profile Analyzer
  -> Jenkinsfile Renderer
  -> GitOps Manifest Renderer
  -> Repository Report Renderer
  -> Static Dashboard Renderer
  -> Redaction Guard

Optional LLM Boundary
  -> Prompt Builder
  -> On-prem LLM Adapter
  -> Recommendation Parser
```

## Public Interfaces

### Existing CLI

```bash
k8s-deploy-agent dry-run --config <config.yaml> --output <dir> [--repo <path>] [--image-tag <tag>]
```

This command remains the canonical non-interactive path.

### Local Console CLI

```bash
k8s-deploy-agent web --host 127.0.0.1 --port 8080
```

The `web` command starts a local server only. Default binding remains loopback unless an operator explicitly chooses another host.

### Config Contract

The UI must produce a payload compatible with the dry-run config model. Sensitive values are represented as:

- credential ID
- environment variable name
- internal endpoint URL without embedded credentials

The UI must not require raw secret values.

## Data Flow

### Dry-run from Web UI

```text
operator form input
  -> config validator
  -> temporary dry-run config or in-memory config object
  -> source repository adapter
  -> repository analyzer
  -> renderers
  -> redaction guard
  -> output directory
  -> UI result model
```

The same analyzer and renderers used by CLI dry-run should be used by web dry-run. UI-specific code should not reimplement Jenkinsfile, GitOps, report, or manifest generation.

### Dockerfile Proposal Planning

Dockerfile generation must not start from a template guess. The repository analyzer must first produce a deterministic build profile per service.

```text
source repository
  -> repository analyzer
  -> normalized build profile
  -> proposal confidence gate
  -> review-only Dockerfile/.dockerignore proposal preview
```

The profile must separate confirmed evidence from inferred values. Low-confidence profiles are blocked from Dockerfile proposal generation. See `docs/DockerfilePlan.md`.

Current dry-run output adds:

```text
dockerfile-proposals/VALIDATION.md
dockerfile-proposals/<service>/Dockerfile
dockerfile-proposals/<service>/.dockerignore
```

These artifacts are local output only. They are not written back to the source repository.

### Asset Preview

```text
dry-run output directory
  -> safe local file reader
  -> syntax-neutral preview panel
```

Preview reads generated local files only. It does not fetch external JS, CSS, images, fonts, schemas, or SaaS resources.

### Validation Checklist

```text
config + analysis + generated files
  -> input validation checks
  -> output validation checks
  -> blocking/non-blocking checklist result
```

Blocking checks include secret redaction failure, missing required config, invalid namespace, missing required generated assets, and write-back target ambiguity.

Dockerfile proposal validation additionally checks that proposal artifacts remain under `dockerfile-proposals/`, contain no secret-like values, and came from BuildProfiles that passed the confidence gate.

## On-prem LLM Boundary

LLM support is optional and advisory.

```text
analysis result + generated asset summary
  -> sanitizer
  -> prompt builder
  -> local/on-prem endpoint adapter
  -> structured recommendation parser
  -> UI review panel
```

Rules:

- Core dry-run must work when LLM is disabled or unreachable.
- The adapter may call only configured local/internal endpoints.
- Prompt inputs must exclude raw secrets and credential values.
- Recommendations are displayed as review text.
- Recommendations do not mutate generated assets automatically.
- Any future apply action must be a separate task with explicit validation and diff preview.

## Write-back Boundary

MVP console can prepare write-back, but actual write-back behavior remains behind gates.

Required gates:

- dry-run completed
- redaction guard passed
- validation checklist has no blocking failures
- target repository/path is explicit
- operator reviewed diff preview

Initial write-back preparation should produce reviewable artifacts, such as:

- export bundle path
- GitOps repository change preview
- source repository Jenkinsfile change preview
- generated report summary
- suggested commit message text

It must not push to source or GitOps repositories without a later explicit implementation task and command path.

## Failure Handling

| Failure | Boundary | Expected Behavior |
|---------|----------|-------------------|
| Invalid config | Config validator | Return field-level errors before execution |
| Clone/auth failure | Source repository adapter | Stop dry-run and show source access failure |
| Analyzer failure | Repository analyzer | Stop generation and show actionable error |
| Renderer failure | Renderer | Stop generation and keep partial output out of write-back path |
| Secret detected | Redaction guard | Block validation and write-back preparation |
| LLM unavailable | LLM adapter | Mark LLM panel unavailable and continue core flow |
| Preview read failure | UI local file reader | Show missing/unreadable asset status |

## Offline Constraints

- Use Python standard library where practical.
- Do not introduce external SaaS calls.
- Do not depend on external CDN, fonts, scripts, or image assets.
- Do not require internet access at runtime.
- Keep generated manifests simple and reviewable.

## Verification Strategy

Document phase:

```bash
test -f docs/PRD.md
test -f docs/UserFlow.md && test -f docs/Architecture.md
```

Regression:

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

Implemented tests cover:

- `web` parser accepts `--host` and `--port`
- form payload validates to dry-run compatible config
- UI dry-run calls the same core pipeline as CLI dry-run
- raw secret-like inputs are rejected before execution
- BuildProfile evidence is rendered in repository reports
- Dockerfile proposal artifacts and validation report are generated as review-only output
- root-level app repositories are detected as service candidates

Future implementation tests should cover:

- LLM unavailable state does not fail dry-run when the LLM panel is added
- failed redaction disables write-back preparation when write-back preparation is added
