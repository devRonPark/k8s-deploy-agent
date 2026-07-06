# User Flow

## Primary Flow

```text
Open operator console
  -> enter project and repository information
  -> run repository analysis
  -> review detected services
  -> review generated assets
  -> run validation checklist
  -> export or prepare write-back
```

## Screens

| Screen | Purpose | Inputs | Outputs |
|--------|---------|--------|---------|
| Project Onboarding | Collect migration inputs | app, repo, registry, GitOps info | validated config |
| Analysis | Show source repository findings | source repo | services and risks |
| Asset Preview | Review generated files | analysis and config | Jenkinsfile/manifests |
| Validation | Block unsafe output | generated files | pass/fail checklist |

## Error States

- Repository clone failure
- Missing credential ID
- Unsupported stack
- Missing Dockerfile
- Secret redaction failure
- LLM endpoint unavailable
