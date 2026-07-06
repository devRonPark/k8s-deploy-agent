# Dockerfile Generation Plan

작성일: 2026-07-06
상태: implemented through review-only proposal preview
범위: repository analysis 기준 정리, deterministic generation gate 정의, review-only Dockerfile/`.dockerignore` proposal artifact 생성

## 목적

Dockerfile은 source repository에 바로 쓰지 않는다. 먼저 repository source code를 분석해 어떤 애플리케이션인지, 어떤 방식으로 빌드되는지, 빌드 결과물이 무엇인지, 무엇을 제외해야 하는지, 어떤 포트를 노출해야 하는지를 결정론적으로 정리한다.

이 문서의 목표는 `repo analysis -> normalized build profile -> human review -> Dockerfile proposal` 흐름을 고정하는 것이다.

## 현재 구현 상태

현재 브랜치 `feature/dockerfile-build-profile` 기준으로 다음 범위가 구현되어 있다.

- `BuildProfile` 모델과 evidence/unresolved question 기록
- Python, Node.js, Java, Go service 후보의 dependency file, lockfile, build tool, runtime command, port evidence 분석
- repository root에 대표 dependency file이 있는 single-service app 감지
- low-confidence 또는 unresolved profile을 차단하는 Dockerfile proposal gate
- review-only `dockerfile-proposals/<service>/Dockerfile` artifact 생성
- review-only `dockerfile-proposals/<service>/.dockerignore` artifact 생성
- `dockerfile-proposals/VALIDATION.md` validation report 생성
- repository analysis report의 `Build Profiles` 및 `Build Profile Evidence` 출력
- dry-run dashboard와 local operator console preview에서 proposal validation 상태 노출

Proposal artifact는 dry-run output directory에만 생성된다. Source repository에는 Dockerfile이나 `.dockerignore`를 쓰지 않는다.

## Dockerfile 작성 기본

일반적으로 Dockerfile은 다음 순서로 구성한다.

1. Base image 선택
2. Working directory 설정
3. Dependency manifest 먼저 복사
4. Dependency install
5. Application source 복사
6. Build command 실행
7. Runtime image 구성
8. Non-root user 설정
9. Exposed port와 startup command 정의

팀들이 보통 따르는 관행:

- build stage와 runtime stage를 분리한다.
- dependency install layer를 source copy보다 앞에 둔다.
- `.dockerignore`로 build context를 줄인다.
- runtime image에는 build toolchain을 넣지 않는다.
- secret 값은 `ARG`, `ENV`, image layer에 넣지 않는다.
- root user 실행을 피한다.
- `latest`처럼 drift가 큰 base tag는 피하고, 조직 표준 tag를 사용한다.
- generated Dockerfile은 바로 적용하지 않고 review 대상 artifact로 둔다.

## 일반적인 Dockerfile 패턴

### Python service

확인할 정보:

- `pyproject.toml`, `requirements.txt`, `poetry.lock`, `uv.lock`
- framework: FastAPI, Flask, Django, Celery worker 등
- start command: `uvicorn`, `gunicorn`, `python -m`, framework command
- port: source config, framework default, existing manifest, README
- dependency install method: `uv`, `pip`, `poetry`

일반 패턴:

```dockerfile
FROM python:<version>-slim AS runtime
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE <port>
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "<port>"]
```

생성 전 gate:

- start module이 확인되지 않으면 Dockerfile proposal을 만들지 않는다.
- port가 추론만 된 경우 `confidence=low`로 표시한다.

### Node.js service

확인할 정보:

- `package.json`
- lockfile: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
- scripts: `build`, `start`, `serve`, `dev`
- framework: Vite, Next.js, Express, NestJS
- build output: `dist`, `.next`, `build`, static assets

일반 패턴:

```dockerfile
FROM node:<version> AS build
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM node:<version>-slim AS runtime
WORKDIR /app
COPY --from=build /app .
EXPOSE <port>
CMD ["npm", "run", "start"]
```

생성 전 gate:

- package manager와 lockfile이 불일치하면 proposal을 block한다.
- `start` script가 없고 static build인지 server runtime인지 확인되지 않으면 block한다.

### Java service

확인할 정보:

- `pom.xml`, `build.gradle`, `gradlew`
- packaging: jar, war
- framework: Spring Boot, Quarkus, plain JVM
- build command: `mvn package`, `./gradlew build`
- artifact path: `target/*.jar`, `build/libs/*.jar`
- port: `server.port`, `application.yml`, default 8080

일반 패턴:

```dockerfile
FROM eclipse-temurin:<version> AS build
WORKDIR /workspace
COPY . .
RUN ./gradlew build

FROM eclipse-temurin:<version>-jre AS runtime
WORKDIR /app
COPY --from=build /workspace/build/libs/*.jar app.jar
EXPOSE <port>
CMD ["java", "-jar", "app.jar"]
```

생성 전 gate:

- artifact path가 단일 파일로 결정되지 않으면 proposal을 block한다.
- wrapper가 없을 때 내부망 build tool availability를 확인해야 한다.

### Go service

확인할 정보:

- `go.mod`
- command package path
- build tags
- CGO requirement
- port and health endpoint

일반 패턴:

```dockerfile
FROM golang:<version> AS build
WORKDIR /src
COPY go.mod go.sum .
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /out/app ./cmd/app

FROM debian:<version>-slim AS runtime
COPY --from=build /out/app /app
EXPOSE <port>
CMD ["/app"]
```

생성 전 gate:

- command package가 여러 개면 service mapping을 사람이 확인해야 한다.
- CGO 사용 여부가 불명확하면 minimal Debian runtime을 우선하고, distroless/static 전환은 사람 검토 대상으로 둔다.

## Repository analysis가 먼저 정리해야 할 정보

각 service candidate마다 다음 profile을 생성한다.

```text
BuildProfile
  service_name
  service_path
  app_type
  framework
  dependency_files
  lockfiles
  build_tool
  build_command
  runtime_command
  build_output
  docker_context
  dockerfile_existing
  ignore_candidates
  exposed_port
  health_endpoint
  confidence
  evidence
  unresolved_questions
```

원칙:

- `evidence`에는 실제 파일 경로와 발견 근거를 기록한다.
- 확인된 사실과 추론을 분리한다.
- `confidence=low`인 profile은 Dockerfile proposal 대상에서 제외한다.
- profile이 deterministic하게 생성되지 않으면 다음 단계로 넘기지 않는다.

### Service discovery coverage

현재 analyzer는 다음 repository shape를 다룬다.

- `backend/`, `frontend/`처럼 하위 directory에 service별 대표 파일이 있는 multi-service repository
- repository root에 `package.json`, `pyproject.toml`, `requirements.txt`, `pom.xml`, `build.gradle`, 또는 `go.mod`가 있는 root-level single-service repository

Root-level service는 service path가 `.`로 기록되며, proposal artifact는 service name 기준으로 `dockerfile-proposals/<service>/` 아래 생성된다.

## 제외 파일 분석 기준

`.dockerignore` 후보는 Dockerfile과 함께 검토되어야 한다.

일반 제외 후보:

- `.git`
- `.pytest_cache`
- `__pycache__`
- `node_modules`
- `.venv`
- `venv`
- `dist`
- `build`
- `target`
- `coverage`
- `.env`
- `.env.*`
- local logs
- IDE metadata

규칙:

- secret-like 파일은 항상 제외 후보에 들어간다.
- build output directory는 runtime copy 대상인지 build context 제외 대상인지 profile에서 구분한다.
- 기존 `.dockerignore`가 있으면 새 파일을 덮어쓰지 않고 proposal diff로만 보여준다.

## Port 분석 기준

port는 다음 순서로 확인한다.

1. 기존 Dockerfile `EXPOSE`
2. Kubernetes manifest `containerPort`
3. framework config
4. application config
5. package/script command line
6. README or docs
7. framework default

규칙:

- 1-5는 `confirmed` 또는 `medium` confidence로 둘 수 있다.
- 6-7만 있으면 `low` confidence로 표시한다.
- port가 여러 개면 Dockerfile proposal을 block하고 review question으로 남긴다.

## Dockerfile proposal gate

Dockerfile proposal은 다음 조건을 모두 만족해야 생성한다.

- service path가 하나로 확정되어 있다.
- app type이 supported stack이다.
- dependency install method가 확정되어 있다.
- build command 또는 runtime command가 확정되어 있다.
- build output 또는 startup target이 확정되어 있다.
- exposed port가 하나로 확정되어 있다.
- raw secret 파일이나 값이 Dockerfile, `.dockerignore`, generated report에 포함되지 않는다.
- proposal은 자동 적용하지 않고 preview artifact로만 생성한다.

현재 gate implementation은 `python`, `node`, `java`, `go` app type만 허용하고, `confidence=low`, unresolved question, missing service path, missing dependency file, missing build tool, missing runtime command, missing exposed port를 block reason으로 기록한다.

## Generated artifacts

Dry-run output에는 다음 proposal artifact가 추가된다.

```text
dockerfile-proposals/VALIDATION.md
dockerfile-proposals/<service>/Dockerfile
dockerfile-proposals/<service>/.dockerignore
```

`VALIDATION.md`는 다음 항목을 확인한다.

- Secret redaction: proposal artifact에 secret-like 값이 없는지
- Review-only output: artifact path가 `dockerfile-proposals/` 아래인지
- Confidence gate: proposal service가 BuildProfile gate를 통과했는지

## 현재 구현하지 않을 것

- Dockerfile 자동 write-back
- source repository 수정
- LLM recommendation 자동 적용
- low-confidence Dockerfile 생성
- Docker build 실행
- base image vulnerability scan
- 조직별 base image policy 자동 결정

## Acceptance

문서 산출물:

```bash
test -f docs/DockerfilePlan.md
```

구현 검증:

```bash
UV_CACHE_DIR=.uv-cache /home/daolts/.local/bin/uv run pytest -q
```

검증 대상:

- profile 생성 테스트
- evidence/source path 테스트
- low-confidence block 테스트
- `.dockerignore` 후보 테스트
- language별 proposal preview 테스트
- secret redaction and review-only validation 테스트

## 참고 기준

- Docker official docs: Building best practices, https://docs.docker.com/build/building/best-practices/
- Docker official docs: Multi-stage builds, https://docs.docker.com/build/building/multi-stage/
- Docker official docs: Optimize cache usage in builds, https://docs.docker.com/build/cache/optimize/
