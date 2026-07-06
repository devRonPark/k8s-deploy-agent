from __future__ import annotations

from k8s_deploy_agent.build_profile import BuildProfile
from k8s_deploy_agent.dockerfile_gate import evaluate_dockerfile_proposal_gate


def render_dockerfile_proposals(profiles: tuple[BuildProfile, ...]) -> dict[str, str]:
    proposals: dict[str, str] = {}
    for profile in profiles:
        gate = evaluate_dockerfile_proposal_gate(profile)
        if not gate.allowed:
            continue
        dockerfile = _render_dockerfile(profile)
        if dockerfile:
            proposals[f"{profile.service_name}/Dockerfile"] = dockerfile
    return proposals


def render_dockerignore_proposals(profiles: tuple[BuildProfile, ...]) -> dict[str, str]:
    proposals: dict[str, str] = {}
    for profile in profiles:
        gate = evaluate_dockerfile_proposal_gate(profile)
        if not gate.allowed or not profile.ignore_candidates:
            continue
        proposals[f"{profile.service_name}/.dockerignore"] = render_dockerignore(profile)
    return proposals


def _render_dockerfile(profile: BuildProfile) -> str | None:
    if profile.app_type == "python":
        return render_python_dockerfile(profile)
    if profile.app_type == "node":
        return render_node_dockerfile(profile)
    if profile.app_type == "java":
        return render_java_dockerfile(profile)
    if profile.app_type == "go":
        return render_go_dockerfile(profile)
    return None


def render_python_dockerfile(profile: BuildProfile) -> str:
    port = profile.exposed_port or 8000
    dependency_file = _dependency_file_name(profile)
    install_command = _install_command(profile, dependency_file)
    runtime_command = _runtime_command(profile, port)
    return "\n".join(
        [
            "FROM python:3.12-slim AS runtime",
            "",
            "WORKDIR /app",
            "",
            f"COPY {dependency_file} .",
            f"RUN {install_command}",
            "",
            "COPY . .",
            "",
            "RUN useradd --create-home --shell /usr/sbin/nologin appuser",
            "USER appuser",
            "",
            f"EXPOSE {port}",
            f"CMD {runtime_command}",
            "",
        ]
    )


def render_node_dockerfile(profile: BuildProfile) -> str:
    port = profile.exposed_port or 3000
    install_command = _node_install_command(profile)
    build_command = profile.build_command or f"{profile.build_tool or 'npm'} run build"
    runtime_command = _node_runtime_command(profile, port)
    copy_lines = ["COPY package.json ."]
    for lockfile in profile.lockfiles:
        copy_lines.append(f"COPY {_file_name(lockfile)} .")
    return "\n".join(
        [
            "FROM node:22 AS build",
            "",
            "WORKDIR /app",
            "",
            *copy_lines,
            f"RUN {install_command}",
            "",
            "COPY . .",
            f"RUN {build_command}",
            "",
            "FROM node:22-slim AS runtime",
            "",
            "WORKDIR /app",
            "ENV NODE_ENV=production",
            "",
            "COPY --from=build /app .",
            "",
            "RUN useradd --create-home --shell /usr/sbin/nologin appuser",
            "USER appuser",
            "",
            f"EXPOSE {port}",
            f"CMD {_shell_command_array(runtime_command)}",
            "",
        ]
    )


def render_java_dockerfile(profile: BuildProfile) -> str:
    port = profile.exposed_port or 8080
    build_command = profile.build_command or _java_build_command(profile)
    build_output = profile.build_output or _java_build_output(profile)
    return "\n".join(
        [
            "FROM eclipse-temurin:21 AS build",
            "",
            "WORKDIR /workspace",
            "",
            "COPY . .",
            f"RUN {build_command}",
            "",
            "FROM eclipse-temurin:21-jre AS runtime",
            "",
            "WORKDIR /app",
            "",
            f"COPY --from=build /workspace/{build_output} app.jar",
            "",
            "RUN useradd --create-home --shell /usr/sbin/nologin appuser",
            "USER appuser",
            "",
            f"EXPOSE {port}",
            'CMD ["java", "-jar", "app.jar"]',
            "",
        ]
    )


def render_go_dockerfile(profile: BuildProfile) -> str:
    port = profile.exposed_port or 8080
    copy_lines = ["COPY go.mod ."]
    if any(path.endswith("go.sum") for path in profile.lockfiles):
        copy_lines.append("COPY go.sum .")
    return "\n".join(
        [
            "FROM golang:1.22 AS build",
            "",
            "WORKDIR /src",
            "",
            *copy_lines,
            "RUN go mod download",
            "",
            "COPY . .",
            f"RUN {profile.build_command or 'CGO_ENABLED=0 go build -o /out/app .'}",
            "",
            "FROM debian:12-slim AS runtime",
            "",
            "WORKDIR /",
            "",
            "COPY --from=build /out/app /app",
            "",
            "RUN useradd --create-home --shell /usr/sbin/nologin appuser",
            "USER appuser",
            "",
            f"EXPOSE {port}",
            'CMD ["/app"]',
            "",
        ]
    )


def render_dockerignore(profile: BuildProfile) -> str:
    lines = [
        "# Generated review-only .dockerignore proposal.",
        "# Review before copying into the source repository.",
        *profile.ignore_candidates,
        "",
    ]
    return "\n".join(dict.fromkeys(lines))


def _dependency_file_name(profile: BuildProfile) -> str:
    for path in profile.dependency_files:
        if path.endswith("requirements.txt"):
            return "requirements.txt"
        if path.endswith("pyproject.toml"):
            return "pyproject.toml"
    return "requirements.txt"


def _file_name(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _install_command(profile: BuildProfile, dependency_file: str) -> str:
    if profile.build_tool == "uv" and dependency_file == "pyproject.toml":
        return "pip install --no-cache-dir uv && uv sync --frozen --no-dev"
    if profile.build_tool == "uv":
        return f"pip install --no-cache-dir -r {dependency_file}"
    if profile.build_tool == "poetry":
        return "pip install --no-cache-dir poetry && poetry install --only main --no-root"
    if dependency_file == "pyproject.toml":
        return "pip install --no-cache-dir ."
    return f"pip install --no-cache-dir -r {dependency_file}"


def _runtime_command(profile: BuildProfile, port: int) -> str:
    command = profile.runtime_command or f"uvicorn app.main:app --host 0.0.0.0 --port {port}"
    command = _command_for_docker_context(profile, command)
    if "--port" not in command:
        command = f"{command} --port {port}"
    return _shell_command_array(command)


def _node_install_command(profile: BuildProfile) -> str:
    if profile.build_tool == "pnpm":
        return "corepack enable && pnpm install --frozen-lockfile"
    if profile.build_tool == "yarn":
        return "corepack enable && yarn install --frozen-lockfile"
    return "npm ci" if any(path.endswith("package-lock.json") for path in profile.lockfiles) else "npm install"


def _node_runtime_command(profile: BuildProfile, port: int) -> str:
    command = profile.runtime_command or f"{profile.build_tool or 'npm'} run start"
    if "--port" not in command:
        command = f"{command} -- --host 0.0.0.0 --port {port}"
    return command


def _java_build_command(profile: BuildProfile) -> str:
    if profile.build_tool == "gradle":
        return "gradle build -x test"
    return "mvn -B package -DskipTests"


def _java_build_output(profile: BuildProfile) -> str:
    if profile.build_tool == "gradle":
        return "build/libs/*.jar"
    return "target/*.jar"


def _command_for_docker_context(profile: BuildProfile, command: str) -> str:
    if not profile.docker_context:
        return command
    context_module = profile.docker_context.replace("/", ".")
    prefix = f"uvicorn {context_module}."
    if command.startswith(prefix):
        return f"uvicorn {command.removeprefix(prefix)}"
    return command


def _shell_command_array(command: str) -> str:
    escaped = command.replace("\\", "\\\\").replace('"', '\\"')
    return f'["sh", "-c", "{escaped}"]'
