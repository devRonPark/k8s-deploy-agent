# Design

## Product Surface

The UI is an operator console for Kubernetes migration preparation, not a marketing page.

## Visual Direction

- Dense, practical, operations-focused layout
- Clear service readiness and validation state
- No external fonts, CDNs, or remote assets
- Works in customer internal networks

## Core Views

| View | Purpose |
|------|---------|
| Project Onboarding | Gather source, GitOps, registry, and namespace inputs |
| Repository Analysis | Show service detection and migration risks |
| Generated Assets | Preview Jenkinsfile and GitOps manifests |
| Validation Checklist | Show secret, namespace, image, and manifest checks |
| LLM Review | Show on-prem LLM recommendations |

## Interaction Rules

- Do not auto-apply LLM recommendations.
- Require explicit review before write-back.
- Highlight unsupported services and missing Dockerfiles.
- Keep secret values out of all UI states.
