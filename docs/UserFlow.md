# Operator Console User Flow

작성일: 2026-07-06
상태: MVP implemented for local console shell, form validation, dry-run execution, preview, and checklist
기준 문서: `docs/ui-ux-plan.md`, `docs/PRD.md`

## Primary Flow

```text
Open local operator console
  -> choose source input mode and enter project/repository inputs
  -> validate credential references and target naming
  -> run dry-run analysis
  -> review detected services, BuildProfiles, and migration risks
  -> review generated CI/GitOps/Kubernetes assets
  -> review Dockerfile/.dockerignore proposal artifacts
  -> run validation checklist
  -> optionally review on-prem LLM recommendations
  -> export dry-run output or prepare gated write-back
```

## Entry Point

Operator starts the console locally.

```bash
k8s-deploy-agent web --host 127.0.0.1 --port 8080
```

The existing CLI dry-run remains available for scripted operation.

```bash
k8s-deploy-agent dry-run --config .agent/config/demo-inputs.example.yaml --output ./out/demo
```

## Screens

| Screen | Purpose | Inputs | Outputs | Blocking Errors |
|--------|---------|--------|---------|-----------------|
| Project Onboarding | Collect migration scope and internal system references | app name, environment, namespace, repo URLs, branches, paths, credential IDs, token env var names | validated config payload | missing required field, raw secret-like input, invalid namespace |
| Repository Access | Confirm source and GitOps access references before execution | source input mode, source repo URL/ref, optional server local repo path, credential ID, optional token env name, GitOps target | access summary | clone/auth failure, missing local path, unreadable local directory, missing credential reference |
| Repository Analysis | Show what the agent found in the source tree | local clone or local repo path | file summary, services, stacks, Dockerfile status, BuildProfile evidence, unsupported risks | no source tree, unsupported structure, analyzer failure |
| Generated Asset Preview | Let operator inspect generated files | dry-run config and analysis result | report, Jenkinsfile, Fleet config, Namespace, Deployment, Service, ConfigMap, Dockerfile proposal artifacts | renderer failure, missing expected generated asset |
| Validation Checklist | Separate review gates from generation | generated files, config metadata, analysis result | pass/fail checklist and blocking reasons | redaction failure, invalid image name, invalid namespace, missing required manifest |
| LLM Review | Optional advisory review from on-prem LLM | sanitized analysis summary and generated asset summaries | recommendations only | endpoint unavailable, malformed response |
| Export / Write-back Preparation | Prepare safe handoff after validation | validated dry-run output | export path, diff preview, write-back readiness summary | failed checklist, missing target repo/path |

## Project Onboarding Fields

| Field | Example | Notes |
|-------|---------|-------|
| application name | `payments-api` | Used in report and generated names |
| environment | `dev` | Operator label |
| target namespace | `payments-dev` | Must remain Kubernetes-compatible |
| source repository URL | `https://gitea.internal/acme/payments-api.git` | Internal URL |
| source branch | `main` | Ref to analyze |
| source input mode | `clone` or `local` | `clone` uses source repo URL/branch; `local` analyzes a server filesystem path |
| local source repository path | `/srv/repos/payments-api` | Used only in `local` mode; dry-run output stays outside the source repo |
| source credential ID | `gitea-source-credential` | Raw secret forbidden |
| source access token env | `K8S_DEPLOY_AGENT_SOURCE_TOKEN` | Environment variable name only |
| GitOps repository URL | `https://gitea.internal/acme/fleet-apps.git` | Internal URL |
| GitOps branch/path | `main/apps/payments-api` | Target location |
| GitOps credential ID | `gitea-gitops-credential` | Raw secret forbidden |
| registry URL/project | `registry.internal/acme` | Image prefix |
| registry credential ID | `suse-registry-credential` | Raw secret forbidden |
| registry CA credential ID | `suse-registry-ca-cert` | Optional ID |

## Validation Flow

Validation runs in two layers.

1. Input validation before dry-run:
   - required values are present
   - namespace and path formats are reviewable
   - credential fields contain IDs or environment variable names, not raw values
   - no external SaaS endpoint is configured for LLM

2. Output validation after dry-run:
   - `assert_no_secret_values` passes
   - expected report, Jenkinsfile, Fleet config, Namespace, Deployment, Service, ConfigMap files exist
   - `dockerfile-proposals/VALIDATION.md` exists and is not blocked
   - proposal artifacts remain under `dockerfile-proposals/`
   - proposal services passed the BuildProfile confidence gate
   - unsupported services and missing Dockerfiles are clearly flagged
   - image names use the configured internal registry/project
   - GitOps path is explicit
   - write-back preparation remains disabled until blocking checks pass

## Error States

| Error | User-facing State | Expected Recovery |
|-------|-------------------|-------------------|
| Repository clone failure | Source access failed | Check URL, branch, credential ID, or token environment variable |
| Local repository path invalid | Source access failed | Enter an existing directory path on the web server filesystem |
| Missing credential ID | Input validation blocked | Enter the credential ID configured in Jenkins/GitOps/registry systems |
| Raw secret-like value detected | Input validation blocked | Replace the value with a credential ID or environment variable name |
| Unsupported stack | Analysis needs review | Operator decides whether to exclude or handle manually |
| Missing Dockerfile | Service needs review | Add Dockerfile manually or exclude service from generated deployment |
| Low-confidence BuildProfile | Proposal blocked | Review unresolved question and update source/config evidence |
| Dockerfile proposal validation blocked | Validation blocked | Inspect `dockerfile-proposals/VALIDATION.md` and fix the profile or generated artifact |
| Renderer failure | Dry-run failed | Inspect error and rerun with corrected config/source tree |
| Secret redaction failure | Validation blocked | Remove secret source from config/generated output before continuing |
| LLM endpoint unavailable | LLM panel unavailable | Continue without LLM recommendations |
| Write-back target missing | Preparation blocked | Provide GitOps/source target and rerun validation |

## LLM Review Flow

LLM review is optional and must not block the non-LLM flow.

```text
analysis result + generated asset summaries
  -> sanitize prompt inputs
  -> call local/on-prem LLM endpoint if configured
  -> parse structured recommendation
  -> show recommendation in review panel
```

LLM recommendations may describe risks or suggested edits. They do not edit config, generated assets, source repository, GitOps repository, or cluster state.

## Completion Criteria

An operator run is complete when:

- dry-run generated the expected assets
- validation checklist has no blocking failures
- operator has reviewed services needing manual attention
- operator has reviewed Dockerfile proposal artifacts when present
- export path or write-back preparation summary is available
- no raw secret appears in UI state, generated files, logs, or reports
