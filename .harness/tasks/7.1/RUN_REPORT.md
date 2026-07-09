# RUN_REPORT.md — Task 7.1

## Summary

- Task: `7.1` — clone 모드에서 source_credential_id 없이 anonymous clone 허용
- 상태: `done`
- 변경: `web.py`의 하드코딩된 FastAPI 데모 URL 전용 예외(`_is_public_sample_clone`)를 URL/branch에 무관하게 credential·token env가 모두 비어 있으면 anonymous로 간주하는 `_is_anonymous_clone`으로 일반화. `config.py`는 변경 불필요로 판명 — placeholder 주입 방식(`public-source`)을 유지해 `DemoConfig`의 `source_credential_id` required 제약을 그대로 둔 채 해결.

## Evidence

| 구분 | 명령 또는 근거 | 결과 | 비고 |
|------|----------------|------|------|
| TDD | `pytest -q tests/test_cli_dry_run.py -k arbitrary_public_clone` (구현 전) | RED | `Missing required config fields: source_credential_id` — 하드코딩된 데모 URL이 아닌 임의 public repo가 거부됨을 확인 |
| Verification: Acceptance | `UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q` | PASS | 50 passed |
| Verification: Tests | 위와 동일 (project 전체 스위트) | PASS | 50 passed, 0 failed |
| Review | - | SKIP | 사용자 요청 흐름상 리뷰 단계 별도 진행 대기 |

## Notes

- 결정: 초기 proposal의 DoD는 `config.py`의 `REQUIRED_FIELDS`에서 `source_credential_id` 제거를 전제했으나, 구현 중 재검토 결과 web.py 쪽 placeholder 주입 범위만 일반화하면 동일한 관찰 가능한 동작(임의 public URL + 빈 credential이 검증을 통과)을 더 작은 변경으로 달성할 수 있어 config.py는 건드리지 않았다. `tasks/index.json`의 7.1 `dod`를 실제 구현에 맞게 갱신함.
- 변경 파일:
  - `web.py` — `_is_public_sample_clone` → `_is_anonymous_clone`으로 교체(URL 하드코딩 제거, credential·token 공란 여부만 판정). `PUBLIC_SAMPLE_REPO_URL`/`PUBLIC_SAMPLE_BRANCH` 상수는 sample 채우기 버튼(`/sample`)에서 여전히 사용되므로 유지.
  - `tests/test_cli_dry_run.py` — `test_console_payload_validation_arbitrary_public_clone_allows_empty_credential` 신규 추가. 기존 `test_console_payload_validation_clone_mode_requires_source_clone_fields`, `test_console_payload_validation_public_github_clone_requires_only_url_and_branch`는 수정 없이 그대로 통과(전자는 token env가 채워져 있어 여전히 credential 필수 케이스를 검증, 후자는 일반화된 로직으로도 동일하게 통과).
  - `tasks/index.json` — Task 7.1 `dod` 텍스트를 실제 구현(“config.py 미변경, PUBLIC_SAMPLE_* 상수 유지”)에 맞게 수정하고 `status`를 `done`으로 전환. `Plans.md`는 `scripts/sync_plans.py`로 재생성.
- 실패/복구: 없음.
- TDD 예외: 해당 없음 (기능 변경이라 TDD 진행).
- 다음 행동: Task 7.2(anonymous clone 인증 실패 시 안내 문구 추가) 진행 대기.
- 최종 갱신: 2026-07-09 14:30 KST
