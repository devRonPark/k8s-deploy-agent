# Decomposition Report

## 요청

`web` console에서 sample 값으로 public GitHub repository를 빠르게 테스트할 수 있게 한다.

- repository: `https://github.com/fastapi/full-stack-fastapi-template.git`
- branch: `main`
- UI: 이 값을 고정으로 채우는 버튼 추가
- 확인: public GitHub repository clone에서는 이 두 값만 필수인지 검증

## 분해 결과

### 6.2 web console public GitHub sample clone preset 추가

이 Task는 operator console의 clone 입력 contract 하나를 바꾼다. 사용자는 버튼으로 public FastAPI sample repository URL과 `main` branch를 채울 수 있고, public GitHub repository clone validation은 source credential ID나 access token env 없이도 통과해야 한다.

완료 기준은 두 가지다.

- `render_operator_console()` HTML에 sample 버튼과 고정 sample 값이 드러난다.
- `validate_console_payload()`가 clone mode에서 public GitHub URL과 branch만 받은 source 입력을 허용한다.

확인 방법은 기존 프로젝트 테스트 명령이다.

```sh
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

## 세분화 판단

하나의 Task로 유지한다. UI 버튼과 validation 변경은 모두 `web` form의 public sample clone contract를 구현하기 위한 같은 관심사이며, 별도 runtime pipeline이나 generated asset format 변경을 요구하지 않는다. 기존 `source_repo.py`의 `git clone --branch <branch> <url>` 실행은 token이 없으면 credential helper를 만들지 않으므로, public repository의 필수 입력 확인은 web/config validation 테스트로 판정할 수 있다.

## 선행 작업

`6.1 operator console 단계형 UI/UX 개편`이 완료되어 있어야 한다. sample 버튼은 현재 단계형 console form 위에 붙는 UX 보강이다.
