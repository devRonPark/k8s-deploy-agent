# Harness State

Updated: 2026-07-09 20:00 KST

## Current Snapshot

- Project: k8s-deploy-agent
- Runtime: Claude Code (harness-work 절차 수동 수행)
- Stack: Python 3.11+, uv, pytest
- Current focus: Task 8.6 dry-run manual-actions.md report 추가
- Task source of truth: `tasks/index.json`

## Active Task

| Task | Status | Notes |
|------|--------|-------|
| 8.6 | done | 신규 `manual_actions.py`의 `render_manual_actions(manifest_plan, image_tag)`가 skipped manifests, unresolved/conflicting ports, required secret keys, stateful/external dependencies, external exposure note, GitOps preview vs Jenkins runtime image tag 차이를 markdown으로 렌더링한다. `cli.py`의 `_write_generated_assets`가 `.agent/reports/manual-actions.md`로 기록한다. |

## Gate Notes

- Task-decomposer: passes; 단일 산출물(새 리포트 렌더러 + cli 연결), 변경 파일은 신규 `manual_actions.py` + `cli.py` 연결부 + 테스트 1건.
- Scope/YAGNI: `report.py`/`ui.py`는 건드리지 않음 — "report와 dashboard를 manifest plan readiness로 전환"은 8.7 스코프. ConfigMap data 채우기도 8.6 DoD에 없어 손대지 않음.
- 핵심 결정:
  - Stateful/External dependency 분류는 `DependencyPlan.kind` 값을 기준으로 직접 나눔: stateful={postgres,mariadb,mysql,redis,mongodb}, external={smtp,object_storage,external_api}. `tasks/index.json` DoD 문구("stateful/external dependencies")를 그대로 반영.
  - "external exposure note"는 confirmed workload 중 `container_port.kind == "reverse_proxy"`인 서비스를 근거로 표시 — nginx 등 reverse proxy로 노출되는 서비스는 보통 외부 진입점이라는 8.4/8.5 설계의 자연스러운 연장.
  - "GitOps preview image tag와 Jenkins runtime image tag 차이"는 `jenkinsfile.py`가 항상 리터럴 `${BUILD_NUMBER}`를 쓰는 것과 dry-run `--image-tag` 값이 다르다는 사실을 표로 병기.
  - 모든 섹션을 markdown 표(`|` 구분)로 렌더링 — `redaction.py`의 `SECRET_ASSIGNMENT_RE`(`key[:=]value` 패턴)가 산문체 `key: value` 표기를 secret leak으로 오탐할 수 있어 회피.
- TDD: RED 확인 — `.agent/reports/manual-actions.md` 파일이 없어 `is_file()` assertion 실패하는 것을 구현 전에 확인.
- 수동 확인: `k8s-deploy-agent dry-run`을 실제로 실행해 리포트 내용 육안 검증 — secret value(`super-secret-value`) 미노출, 각 섹션 정상 표시 확인.

## Verification Command

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q tests/test_cli_dry_run.py -k manual_actions
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

## Important Constraints

- Preserve air-gapped/on-premise operation.
- Do not introduce external SaaS dependencies.
- Do not place secret values in config, generated files, UI, logs, or tests. — `assert_no_secret_values`가 `_write_generated_assets`에서 여전히 전체 generated dict를 검사.

## Review Notes

- Self-review (quality-gates.md Review Gate 기준).
- Spec compliance: DoD의 6개 항목(skipped manifests / unresolved·conflicting ports / required secret keys / stateful·external dependencies / external exposure note / image tag 차이) 모두 테스트로 직접 검증.
- Code quality: blocker 없음. `build_workload_manifest_plans`가 `render_gitops_manifests` 내부와 `cli.py`에서 각각 한 번씩(총 2회) 호출되어 repo 파일을 중복으로 다시 읽는 비효율이 있음 — `render_gitops_manifests`가 `manifest_plan`을 인자로 받도록 리팩터링하면 해소되지만 8.5 시그니처 변경이 필요해 8.6 스코프 밖으로 남김.
