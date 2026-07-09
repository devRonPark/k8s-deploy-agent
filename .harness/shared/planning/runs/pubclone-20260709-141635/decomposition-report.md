# Decomposition Report — pubclone-20260709-141635

## 요청

`docs/PRD.md` R14와 2026-07-09 Decisions 3건을 실행 가능한 Task로 반영한다. 배경 버그: operator console에서 실제 public repository URL(하드코딩된 FastAPI 데모 URL이 아닌)을 clone 모드로 입력하면, 검증 단계에서 `Missing required config fields: source_credential_id`로 거부되어 사용자가 기대한 "검증 통과 -> dry-run 정상 완료" 흐름이 깨졌다.

## 근본 원인

- `config.py`의 `REQUIRED_FIELDS`가 `source_credential_id`를 무조건 필수로 요구한다.
- `web.py`의 `_is_public_sample_clone`이 FastAPI 데모 URL/branch 조합 하나만 예외로 인정하고, 그 외 public repository URL은 동일한 방식으로 거부한다.
- `source_repo.py`의 실제 clone 로직은 이미 credential이 비어 있으면 anonymous clone을 시도하도록 되어 있어, 문제는 validation 계층에만 있다.

## Task 목록

### 7.1 — clone 모드에서 source_credential_id 없이 anonymous clone 허용

- **완료 기준**: `config.py`에서 `source_credential_id`가 required 목록에서 빠지고, `web.py`는 특정 URL 예외 없이 "credential/token이 모두 비어 있으면 anonymous로 간주" 규칙을 일반 적용한다. 하드코딩된 데모 URL 특수 케이스(`_is_public_sample_clone`, `PUBLIC_SAMPLE_REPO_URL`, `PUBLIC_SAMPLE_BRANCH`)는 삭제한다.
- **확인 방법**: 임의의 public repository URL + branch만 입력한 payload가 `validate_console_payload`를 통과하는 테스트, 그리고 기존에 credential 필수를 전제로 하던 테스트(`test_console_payload_validation_clone_mode_requires_source_clone_fields`, `test_console_payload_validation_public_github_clone_requires_only_url_and_branch`)를 새 동작에 맞게 갱신해 `UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q`로 확인한다.
- **먼저 끝나야 할 작업**: 없음.

### 7.2 — anonymous clone 인증 실패 시 안내 문구 추가

- **완료 기준**: `source_repo.py`의 `clone_source_repository`가 credential/token 없이 시도한 clone이 실패하면, 에러 메시지에 "private repository면 source credential ID를 입력하세요" 안내 문구가 포함된다. credential/token이 있었던 실패 경로는 문구를 추가하지 않는다.
- **확인 방법**: anonymous 상태(빈 `source_credential_id`)로 존재하지 않는/접근 불가한 저장소를 clone 시도해 발생하는 `ValueError` 메시지에 안내 문구가 포함되는지 확인하는 테스트를 추가하고 `UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q`로 확인한다.
- **먼저 끝나야 할 작업**: 7.1 — anonymous 상태의 `DemoConfig`(빈 `source_credential_id`)가 정상 경로로 생성 가능해야 이 Task의 실패 시나리오를 재현할 수 있다.

## 분리 이유

두 Task는 같은 버그에서 출발하지만 관심사가 다르다. 7.1은 검증/스키마 계층(무엇을 필수로 요구하는가)이고, 7.2는 실패 시 사용자에게 보여줄 에러 메시지 UX다. 각각 독립적으로 관찰 가능한 산출물과 acceptance를 가지므로 하나로 묶지 않았다.

## 범위에서 제외한 것

- Public/Private 명시적 토글 UI 추가 — anonymous clone 기본 허용 방식을 채택하기로 확정했으므로 불필요 (PRD Decision 참고).
- GitOps/registry credential 필수 여부 변경 — 이번 버그와 무관하며 이미 별도 placeholder 패턴(R13)으로 처리되어 있다.
