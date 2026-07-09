# Harness State

Updated: 2026-07-09 19:15 KST

## Current Snapshot

- Project: k8s-deploy-agent
- Runtime: Claude Code (harness-work 절차 수동 수행)
- Stack: Python 3.11+, uv, pytest
- Current focus: Task 8.5 GitOps renderer를 WorkloadManifestPlan 기반으로 전환
- Task source of truth: `tasks/index.json`

## Active Task

| Task | Status | Notes |
|------|--------|-------|
| 8.5 | done | `gitops.py`가 `RepositoryAnalysis.services` 직접 순회 + `service.stack=="unsupported" or not service.dockerfile` 게이트 + 하드코딩 포트 80 fallback을 제거하고, `build_workload_manifest_plans(config, analysis, image_tag)`의 `ManifestPlan.confirmed`만 순회해 Deployment/Service/ConfigMap을 렌더링한다. containerPort/port/targetPort는 `WorkloadManifestPlan.container_port.value`(evidence 기반)를 쓴다. |

## Gate Notes

- Task-decomposer: passes; 단일 산출물(`render_gitops_manifests` 내부 로직 전환), 변경 파일은 `gitops.py` + 신규 테스트 1개.
- Scope/YAGNI: 함수 시그니처(`render_gitops_manifests(config, analysis, image_tag)`) 유지 — `cli.py`/`jenkinsfile.py` 호출부 변경 없음. ConfigMap `data`를 `EnvVarPlan`으로 채우는 건 8.5 DoD에 없어 손대지 않음(8.6/8.7 스코프로 남김).
- 회귀 확인: `tests/test_cli_dry_run.py`의 기존 fixture(`write_sample_repo`)는 이미 `backend`(EXPOSE 8000)/`frontend`(EXPOSE 3000) Dockerfile evidence를 갖고 있어 confirmed 판정에 문제없음 — 파일 존재 assertion들이 수정 없이 그대로 통과.
- TDD: RED 확인 — 신규 테스트 3건이 기존 하드코딩 80/`not service.dockerfile` 게이트 때문에 실패하는 것을 구현 전에 확인.

## Verification Command

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q tests/test_gitops_manifest_plan.py
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

## Important Constraints

- Preserve air-gapped/on-premise operation.
- Do not introduce external SaaS dependencies.
- source/GitOps write-back 자동 실행 없음 — 이번 Task는 in-memory 매니페스트 dict 생성까지만 다룬다(실제 GitOps repo push는 범위 밖).

## Review Notes

- Self-review (quality-gates.md Review Gate 기준).
- Spec compliance: DoD 4항목(services 직접 추측 제거 / 80 fallback 제거 / Deployment·Service·ConfigMap 렌더링 유지 / confirmed port를 containerPort·targetPort에 사용) 모두 테스트로 직접 검증.
- Code quality: blocker 없음. `analyzer.py`의 `ServiceCandidate.stack == "unsupported"`(Go 모듈) 필드는 더 이상 gitops.py에서 참조하지 않음 — WorkloadManifestPlan.confirmed가 이를 자연히 대체(포트 근거 없으면 confirmed 자체가 안 됨).
- 잔여 위험: ConfigMap `data`가 여전히 빈 오브젝트(`{}`) — 8.6/8.7에서 EnvVarPlan 기반으로 채울지 별도 결정 필요.
