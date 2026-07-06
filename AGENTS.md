# k8s-deploy-agent - Codex Harness Rules

## Project Overview

`k8s-deploy-agent` automates repetitive Kubernetes migration preparation work in customer on-premise or air-gapped environments.

The agent receives access to an application source repository, analyzes the repository, and generates initial CI/CD and GitOps assets for running the application on Kubernetes:

- repository analysis report
- Jenkinsfile for Jenkins Kubernetes Plugin based CI
- Kaniko image build/push commands
- Rancher Fleet GitOps manifests
- Kubernetes Namespace, Deployment, Service, and ConfigMap manifests
- dry-run dashboard for operator review
- secret redaction checks

Future work will connect this agent to an on-premise LLM running on a Dell Pro Max GB10 device brought into the customer environment.

## Runtime

- Primary agent runtime: Codex CLI
- Language: Python 3.11+
- Package manager: uv
- Test command: `UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q`
- Entry point: `k8s-deploy-agent`

## Repository Layout

```text
k8s-deploy-agent/
├── analyzer.py
├── cli.py
├── config.py
├── gitops.py
├── jenkinsfile.py
├── redaction.py
├── report.py
├── source_repo.py
├── ui.py
├── tests/
├── docs/
├── agents/
├── .harness/
├── Plans.md
├── harness.toml
└── pyproject.toml
```

The installable package maps `k8s_deploy_agent` to the repository root through `pyproject.toml`.

## Language Rules

- User-facing responses should be Korean unless the user asks otherwise.
- Code, file paths, commands, config keys, and product names should stay in their native spelling.
- Keep explanations concise and operational.

## Engineering Rules

- Preserve offline/on-premise operation. Do not introduce external SaaS calls.
- Do not store secret values in config, generated files, logs, UI, or tests.
- Use credential IDs or environment variable names instead of raw credentials.
- Keep dry-run behavior deterministic and safe.
- Prefer Python standard library unless a dependency clearly earns its cost.
- Keep generated manifests simple and reviewable.
- Keep source repository write-back and GitOps write-back behind explicit validation gates.

## Harness Workflow

`Plans.md` is the task status source of truth.

Allowed task states:

- `cc:TODO`
- `cc:WIP`
- `cc:완료`

Before implementation:

1. Read `.harness/STATE.md`.
2. Read recent `.harness/LESSONS.md` entries.
3. Check `Plans.md` for the relevant task.
4. If the task is too broad, use `agents/task-decomposer.md` and split it before implementation.

After implementation:

1. Run the task Acceptance command if present.
2. Run the project test command.
3. Update `.harness/LOG.md` for meaningful work or errors.
4. Update `.harness/LESSONS.md` when an error produced a reusable prevention rule.
5. Update `.harness/CONTEXT_INDEX.md` when adding or changing durable files.

## Test Rules

Default verification command:

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

For UI/dashboard changes, also generate dry-run output and inspect `index.html` when practical.

## Planning Rules

Use `agents/task-decomposer.md` before writing broad tasks into `Plans.md`.

Good tasks:

- change one concern
- have an objective DoD
- have a runnable Acceptance command
- can fit in one focused PR

Avoid tasks that combine repository analysis, UI, LLM, CI, and write-back in one row.

## Review Rules

Review should prioritize:

- secret leakage
- unsafe write-back behavior
- air-gapped runtime regressions
- generated Jenkinsfile or manifest correctness
- missing tests for behavior changes
- drift between `Plans.md`, `.harness/`, and implementation

## UI/UX Direction

The UI should evolve into an operator console for on-premise Kubernetes migration work.

Current scope:

- static dry-run dashboard

Future scope after harness adoption:

- local web operator console
- config input flow
- dry-run execution
- generated asset preview
- validation checklist
- on-prem LLM recommendation panel
- controlled write-back preparation

See `docs/ui-ux-plan.md`.
