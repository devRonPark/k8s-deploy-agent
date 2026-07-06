# Architecture

## Context

`k8s-deploy-agent` runs inside customer-controlled on-premise environments and should remain useful without internet access.

## Components

```text
CLI / Local Web UI
  -> Config Loader
  -> Source Repo Adapter
  -> Repository Analyzer
  -> Asset Renderers
  -> Redaction Guard
  -> Optional On-prem LLM Adapter
```

## Boundaries

- Core generation must not require LLM availability.
- LLM recommendations are advisory unless a later task adds explicit apply controls.
- Secret values must not cross into generated files or logs.

## Verification

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```
