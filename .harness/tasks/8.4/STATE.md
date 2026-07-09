# Harness State

Updated: 2026-07-09 18:40 KST

## Current Snapshot

- Project: k8s-deploy-agent
- Runtime: Claude Code (harness-work 절차를 수동 수행, `.agents/skills/harness-work`는 Codex 전용이라 Claude 스킬로 등록되어 있지 않음)
- Stack: Python 3.11+, uv, pytest
- Current focus: Task 8.4 WorkloadManifestPlan builder 추가
- Task source of truth: `tasks/index.json`

## Active Task

| Task | Status | Notes |
|------|--------|-------|
| 8.4 | done | `build_workload_manifest_plans(config, analysis, image_tag)`가 service별 BuildProfile(8.1), PortCandidate(8.2), EnvVarPlan/DependencyPlan(8.3)을 결합해 `WorkloadManifestPlan`을 만들고, `ManifestPlan.confirmed`/`unresolved_questions`를 반환한다. |

## Gate Notes

- Task-decomposer: passes; 단일 산출물(`build_workload_manifest_plans`), 변경 파일 2개(`manifest_plan.py`, `tests/test_manifest_plan.py`), 기존 8.1/8.2/8.3 산출물만 조합.
- Scope/YAGNI: 새 프레임워크·추상화 없음. `WorkloadManifestPlan.workloads`/`confirmed`/`unresolved_questions` 세 필드는 각각 8.5/8.6/8.7 DoD가 명시적으로 소비를 예고한 필드만 포함.
- 핵심 결정: container port confirmation은 `BuildProfile.exposed_port`(narrow: Dockerfile EXPOSE + 좁은 app_type config 목록만 확인)가 아니라 `collect_port_candidates`(8.2, nginx/compose/package script 포함)를 유일한 근거로 사용. `BuildProfile.confirmed` 여부와 무관하게 confirmed를 판정 — nginx 리버스 프록시로만 노출되는 프런트엔드(예: fastapi-template)가 build_tool/runtime_command 부재로 build_profile이 medium 상태여도 실제 포트 근거가 있으면 confirmed 되도록 하기 위함(Week 8.9 fixture 요구사항과 정합).
- container port 선정 우선순위: `reverse_proxy` > `container` > `config` (confidence == "confirmed"만). 같은 tier에 서로 다른 값이 여러 개면 confirmed 대신 "conflicting confirmed container ports" unresolved 사유를 남긴다.
- TDD: RED 확인 — `build_workload_manifest_plans` import 실패(ImportError)를 구현 전에 확인. 이후 최소 구현으로 green.

## Verification Command

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q tests/test_manifest_plan.py -k workload
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

## Important Constraints

- Preserve air-gapped/on-premise operation.
- Do not introduce external SaaS dependencies.
- Do not place secret values in config, generated files, UI, logs, or tests. (테스트에서 evidence 문자열에 raw secret 값이 없음을 assert로 확인)
- source/GitOps write-back 자동 실행 없음 — 이번 Task는 순수 model/builder이며 렌더링은 8.5에서 다룬다.

## Review Notes

- Self-review (별도 subagent 없이 세션 내 진행, quality-gates.md Review Gate 기준 적용).
- Spec compliance: DoD의 "Dockerfile proposal만으로는 confirmed manifest를 만들지 않는다" 조건을 `test_workload_manifest_plan_does_not_confirm_from_dockerfile_presence_alone`로 직접 검증.
- Code quality: blocker 없음. 잔여 위험 — `unresolved` 필터링이 analyzer.py의 정확한 문자열 `"exposed port is not confirmed"`에 결합되어 있음(코드에 이유 주석 남김); analyzer.py 쪽 문구가 바뀌면 이 필터가 조용히 깨질 수 있다.
- 잔여 위험(설계 판단, blocker 아님): `WorkloadManifestPlan.confirmed`는 오직 container_port 존재 여부로만 결정하고 build_tool/runtime_command 미확정은 confirmed를 막지 않는다. 8.5(GitOps 렌더링) 단계에서 이미지 빌드 가능 여부까지 확인이 필요해지면 이 게이트를 재검토해야 한다.
