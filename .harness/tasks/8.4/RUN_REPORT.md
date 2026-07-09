# RUN_REPORT.md — Task 8.4

## Summary

- Task: `8.4`
- 상태: `done`
- 변경: `manifest_plan.py`에 `WorkloadManifestPlan`/`ManifestPlan` 모델과 `build_workload_manifest_plans(config, analysis, image_tag)`를 추가. 8.1(BuildProfile)·8.2(PortCandidate)·8.3(EnvVarPlan/DependencyPlan) 산출물을 service별로 결합하고, evidence 기반 container port 선택으로 confirmed 여부를 판정. 관련 테스트 5개를 `tests/test_manifest_plan.py`에 추가.

## Evidence

| 구분 | 명령 또는 근거 | 결과 | 비고 |
|------|----------------|------|------|
| TDD | `uv run pytest -q tests/test_manifest_plan.py -k workload` (구현 전) | RED | `ImportError: cannot import name 'build_workload_manifest_plans'` |
| Verification: Acceptance | `UV_CACHE_DIR=.uv-cache uv run pytest -q tests/test_manifest_plan.py -k workload` | PASS | 5 passed, 6 deselected |
| Verification: Tests | `UV_CACHE_DIR=.uv-cache uv run pytest -q` | PASS | 64 passed |
| Review | self-review (quality-gates.md Review Gate 기준) | APPROVE | Spec compliance / Code quality 모두 blocker 없음, 잔여 위험 2건은 STATE.md 참고 |

## Notes

- 결정: container port 확정은 `BuildProfile.exposed_port`가 아니라 `collect_port_candidates`(8.2)만을 근거로 삼는다. 이유는 STATE.md "핵심 결정" 참고 — nginx 리버스 프록시 전용 프런트엔드가 build_profile 확정 여부와 무관하게 confirmed 되어야 하기 때문.
- 변경 파일:
  - `manifest_plan.py` — `WorkloadManifestPlan`, `ManifestPlan`, `build_workload_manifest_plans`, `_build_workload_plan`, `_select_container_port` 추가.
  - `tests/test_manifest_plan.py` — workload 조합/nginx confirmed/Dockerfile-only 미확정/포트 충돌/aggregate 테스트 5건 추가.
  - `tasks/index.json` — Task 8.4 상태 `todo` → `done`.
  - `Plans.md` — `scripts/sync_plans.py` 재실행으로 재생성.
- 실패/복구: 없음(RED 확인 후 1회 구현으로 green).
- TDD 예외: 해당 없음(behavior 변경이므로 TDD 적용).
- 다음 행동: Task 8.5(GitOps renderer를 WorkloadManifestPlan 기반으로 전환)로 이어간다. gitops.py의 `not service.dockerfile` 게이트와 하드코딩된 포트 80 fallback을 `ManifestPlan.confirmed`/`WorkloadManifestPlan.container_port`로 교체해야 한다.
- 최종 갱신: 2026-07-09 18:40 KST
