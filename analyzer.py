from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from k8s_deploy_agent.build_profile import BuildProfile, ProfileEvidence


@dataclass(frozen=True)
class ServiceCandidate:
    name: str
    path: Path
    stack: str
    reason: str
    dockerfile: Path | None = None


@dataclass(frozen=True)
class RepositoryAnalysis:
    root: Path
    file_tree: tuple[str, ...]
    services: tuple[ServiceCandidate, ...]
    build_profiles: tuple[BuildProfile, ...] = ()

    @property
    def service_names(self) -> list[str]:
        return [service.name for service in self.services]

    def service(self, name: str) -> ServiceCandidate:
        for service in self.services:
            if service.name == name:
                return service
        raise KeyError(name)


def analyze_repository(root: str | Path) -> RepositoryAnalysis:
    root_path = Path(root).resolve()
    file_tree = tuple(_collect_file_tree(root_path))
    services = tuple(_detect_services(root_path))
    build_profiles = tuple(_build_profile(root_path, service) for service in services)
    return RepositoryAnalysis(root=root_path, file_tree=file_tree, services=services, build_profiles=build_profiles)


def _collect_file_tree(root: Path) -> list[str]:
    paths: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or _is_ignored(path, root):
            continue
        paths.append(path.relative_to(root).as_posix())
    return sorted(paths)


def _detect_services(root: Path) -> list[ServiceCandidate]:
    services: list[ServiceCandidate] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        candidate = _service_from_directory(path)
        if candidate:
            services.append(candidate)
    if services:
        return services

    root_candidate = _service_from_directory(root)
    if root_candidate:
        services.append(root_candidate)
    return services


def _service_from_directory(path: Path) -> ServiceCandidate | None:
    dockerfile = path / "Dockerfile"
    dockerfile_path = dockerfile if dockerfile.is_file() else None

    if (path / "package.json").is_file():
        return ServiceCandidate(path.name, path, "node", "package.json", dockerfile_path)
    if (path / "pyproject.toml").is_file() or (path / "requirements.txt").is_file():
        return ServiceCandidate(path.name, path, "python", "python dependency file", dockerfile_path)
    if (path / "pom.xml").is_file() or (path / "build.gradle").is_file():
        return ServiceCandidate(path.name, path, "java", "java build file", dockerfile_path)
    if (path / "go.mod").is_file():
        return ServiceCandidate(path.name, path, "unsupported", "unsupported Go module", dockerfile_path)
    return None


def _build_profile(root: Path, service: ServiceCandidate) -> BuildProfile:
    service_path = service.path.relative_to(root).as_posix()
    app_type = _profile_app_type(service)
    dependency_files = tuple(_existing_relative(root, service.path, _dependency_candidates(app_type)))
    lockfiles = tuple(_existing_relative(root, service.path, _lockfile_candidates(app_type)))
    dockerfile_existing = None
    evidence: list[ProfileEvidence] = []

    evidence.append(
        ProfileEvidence(
            field="app_type",
            path=service_path,
            value=app_type,
            reason=service.reason,
        )
    )
    for path in dependency_files:
        evidence.append(
            ProfileEvidence(
                field="dependency_files",
                path=path,
                value=Path(path).name,
                reason="dependency manifest detected",
            )
        )
    for path in lockfiles:
        evidence.append(
            ProfileEvidence(
                field="lockfiles",
                path=path,
                value=Path(path).name,
                reason="lockfile detected",
            )
        )

    if service.dockerfile:
        dockerfile_existing = service.dockerfile.relative_to(root).as_posix()
        evidence.append(
            ProfileEvidence(
                field="dockerfile_existing",
                path=dockerfile_existing,
                value="Dockerfile",
                reason="existing Dockerfile detected",
            )
        )

    build_tool = _build_tool(app_type, dependency_files, lockfiles)
    if build_tool:
        evidence.append(
            ProfileEvidence(
                field="build_tool",
                path=service_path,
                value=build_tool,
                reason="build tool selected from dependency files and lockfiles",
            )
        )

    framework, framework_evidence = _framework(root, service.path, app_type)
    evidence.extend(framework_evidence)
    build_command, build_output, build_evidence = _build_command_and_output(root, service.path, app_type, build_tool, framework)
    evidence.extend(build_evidence)
    runtime_command, runtime_evidence = _runtime_command(root, service.path, app_type, build_tool, framework)
    evidence.extend(runtime_evidence)
    exposed_port, port_evidence = _exposed_port(root, service.path, service.dockerfile, app_type)
    evidence.extend(port_evidence)

    unresolved = []
    if not dependency_files:
        unresolved.append("dependency files are not confirmed")
    if build_tool is None:
        unresolved.append("build tool is not confirmed")
    if runtime_command is None:
        unresolved.append("runtime command is not confirmed")
    if exposed_port is None:
        unresolved.append("exposed port is not confirmed")

    if dependency_files and build_tool and runtime_command and exposed_port is not None:
        confidence = "confirmed"
    else:
        confidence = "medium" if dependency_files and build_tool else "low"
    return BuildProfile(
        service_name=service.name,
        service_path=service_path,
        app_type=app_type,
        framework=framework,
        dependency_files=dependency_files,
        lockfiles=lockfiles,
        build_tool=build_tool,
        build_command=build_command,
        runtime_command=runtime_command,
        build_output=build_output,
        docker_context=service_path,
        dockerfile_existing=dockerfile_existing,
        ignore_candidates=_ignore_candidates(app_type),
        exposed_port=exposed_port,
        confidence=confidence,
        evidence=tuple(evidence),
        unresolved_questions=tuple(unresolved),
    )


def _profile_app_type(service: ServiceCandidate) -> str:
    if service.stack == "unsupported" and (service.path / "go.mod").is_file():
        return "go"
    return service.stack


def _dependency_candidates(app_type: str) -> tuple[str, ...]:
    return {
        "python": ("pyproject.toml", "requirements.txt"),
        "node": ("package.json",),
        "java": ("pom.xml", "build.gradle", "build.gradle.kts"),
        "go": ("go.mod",),
    }.get(app_type, ())


def _lockfile_candidates(app_type: str) -> tuple[str, ...]:
    return {
        "python": ("uv.lock", "poetry.lock", "Pipfile.lock"),
        "node": ("package-lock.json", "yarn.lock", "pnpm-lock.yaml"),
        "java": ("gradle.lockfile",),
        "go": ("go.sum",),
    }.get(app_type, ())


def _existing_relative(root: Path, service_path: Path, names: tuple[str, ...]) -> list[str]:
    found = []
    for name in names:
        path = service_path / name
        if path.is_file():
            found.append(path.relative_to(root).as_posix())
    return found


def _build_tool(app_type: str, dependency_files: tuple[str, ...], lockfiles: tuple[str, ...]) -> str | None:
    file_names = {Path(path).name for path in (*dependency_files, *lockfiles)}
    if app_type == "python":
        if "uv.lock" in file_names:
            return "uv"
        if "poetry.lock" in file_names:
            return "poetry"
        if "requirements.txt" in file_names:
            return "pip"
        if "pyproject.toml" in file_names:
            return "python"
    if app_type == "node":
        if "pnpm-lock.yaml" in file_names:
            return "pnpm"
        if "yarn.lock" in file_names:
            return "yarn"
        if "package-lock.json" in file_names or "package.json" in file_names:
            return "npm"
    if app_type == "java":
        if any(name.startswith("build.gradle") for name in file_names):
            return "gradle"
        if "pom.xml" in file_names:
            return "maven"
    if app_type == "go" and "go.mod" in file_names:
        return "go"
    return None


def _ignore_candidates(app_type: str) -> tuple[str, ...]:
    common = (".git", ".env", ".env.*", ".pytest_cache", "__pycache__", "coverage", "*.log")
    app_specific = {
        "python": (".venv", "venv", "*.pyc"),
        "node": ("node_modules", "dist", "build"),
        "java": ("target", "build", ".gradle"),
        "go": ("bin", "dist"),
    }.get(app_type, ())
    return tuple(dict.fromkeys((*common, *app_specific)))


def _framework(root: Path, service_path: Path, app_type: str) -> tuple[str | None, list[ProfileEvidence]]:
    evidence: list[ProfileEvidence] = []
    if app_type == "python":
        for name in ("requirements.txt", "pyproject.toml"):
            path = service_path / name
            text = _read_text(path)
            if "fastapi" in text.lower():
                relative = path.relative_to(root).as_posix()
                evidence.append(ProfileEvidence("framework", relative, "fastapi", "FastAPI dependency detected"))
                return "fastapi", evidence
            if "flask" in text.lower():
                relative = path.relative_to(root).as_posix()
                evidence.append(ProfileEvidence("framework", relative, "flask", "Flask dependency detected"))
                return "flask", evidence
    if app_type == "node":
        package_json = _read_package_json(service_path / "package.json")
        dependencies = {
            **package_json.get("dependencies", {}),
            **package_json.get("devDependencies", {}),
        }
        for dependency, framework in (("next", "next"), ("vite", "vite"), ("express", "express"), ("@nestjs/core", "nestjs")):
            if dependency in dependencies:
                relative = (service_path / "package.json").relative_to(root).as_posix()
                evidence.append(ProfileEvidence("framework", relative, framework, f"{dependency} dependency detected"))
                return framework, evidence
    if app_type == "java":
        for name, framework in (("spring-boot", "spring-boot"), ("quarkus", "quarkus")):
            for path in (service_path / "pom.xml", service_path / "build.gradle", service_path / "build.gradle.kts"):
                text = _read_text(path)
                if name in text:
                    relative = path.relative_to(root).as_posix()
                    evidence.append(ProfileEvidence("framework", relative, framework, f"{framework} build file marker detected"))
                    return framework, evidence
    return None, evidence


def _runtime_command(
    root: Path,
    service_path: Path,
    app_type: str,
    build_tool: str | None,
    framework: str | None,
) -> tuple[str | None, list[ProfileEvidence]]:
    if app_type == "node":
        package_json = _read_package_json(service_path / "package.json")
        scripts = package_json.get("scripts", {})
        if isinstance(scripts, dict) and scripts.get("start"):
            command = f"{build_tool or 'npm'} run start"
            path = (service_path / "package.json").relative_to(root).as_posix()
            return command, [ProfileEvidence("runtime_command", path, command, "package.json scripts.start detected")]
    if app_type == "python" and framework == "fastapi":
        app_module = _fastapi_app_module(root, service_path)
        if app_module:
            command = f"uvicorn {app_module}:app --host 0.0.0.0"
            return command, [
                ProfileEvidence("runtime_command", f"{app_module.replace('.', '/')}.py", command, "FastAPI app object detected")
            ]
    if app_type == "java":
        command = "java -jar app.jar"
        return command, [ProfileEvidence("runtime_command", service_path.relative_to(root).as_posix(), command, "JVM service detected")]
    if app_type == "go":
        command = "/app"
        return command, [ProfileEvidence("runtime_command", service_path.relative_to(root).as_posix(), command, "Go service detected")]
    return None, []


def _build_command_and_output(
    root: Path,
    service_path: Path,
    app_type: str,
    build_tool: str | None,
    framework: str | None,
) -> tuple[str | None, str | None, list[ProfileEvidence]]:
    evidence: list[ProfileEvidence] = []
    service_relative = service_path.relative_to(root).as_posix()
    if app_type == "node":
        package_json_path = service_path / "package.json"
        package_json = _read_package_json(package_json_path)
        scripts = package_json.get("scripts", {})
        if isinstance(scripts, dict) and scripts.get("build"):
            command = f"{build_tool or 'npm'} run build"
            output = ".next" if framework == "next" else ("dist" if framework == "vite" else "build")
            relative = package_json_path.relative_to(root).as_posix()
            evidence.append(ProfileEvidence("build_command", relative, command, "package.json scripts.build detected"))
            evidence.append(ProfileEvidence("build_output", relative, output, "framework build output selected"))
            return command, output, evidence
    if app_type == "java":
        if build_tool == "maven":
            command = "mvn -B package -DskipTests"
            output = "target/*.jar"
        elif build_tool == "gradle":
            command = "./gradlew build -x test" if (service_path / "gradlew").is_file() else "gradle build -x test"
            output = "build/libs/*.jar"
        else:
            return None, None, evidence
        evidence.append(ProfileEvidence("build_command", service_relative, command, "JVM build tool detected"))
        evidence.append(ProfileEvidence("build_output", service_relative, output, "JVM jar output pattern selected"))
        return command, output, evidence
    if app_type == "go":
        command = "CGO_ENABLED=0 go build -o /out/app ."
        output = "/out/app"
        evidence.append(ProfileEvidence("build_command", service_relative, command, "Go module build command selected"))
        evidence.append(ProfileEvidence("build_output", service_relative, output, "Go binary output selected"))
        return command, output, evidence
    return None, None, evidence


def _exposed_port(root: Path, service_path: Path, dockerfile: Path | None, app_type: str) -> tuple[int | None, list[ProfileEvidence]]:
    if dockerfile:
        match = re.search(r"(?im)^\s*EXPOSE\s+([0-9]+)\b", _read_text(dockerfile))
        if match:
            port = int(match.group(1))
            return port, [
                ProfileEvidence("exposed_port", dockerfile.relative_to(root).as_posix(), str(port), "Dockerfile EXPOSE detected")
            ]
    for relative_name in _port_config_candidates(app_type):
        path = service_path / relative_name
        port = _port_from_text(_read_text(path))
        if port is not None:
            return port, [
                ProfileEvidence("exposed_port", path.relative_to(root).as_posix(), str(port), "application config port detected")
            ]
    return None, []


def _port_config_candidates(app_type: str) -> tuple[str, ...]:
    return {
        "python": (".env", "app/main.py", "main.py"),
        "node": ("package.json", ".env", "vite.config.js", "vite.config.ts"),
        "java": ("src/main/resources/application.yml", "src/main/resources/application.properties"),
        "go": (".env", "config.yaml"),
    }.get(app_type, ())


def _port_from_text(text: str) -> int | None:
    if not text:
        return None
    patterns = (
        r"(?im)^\s*server\.port\s*=\s*([0-9]+)\s*$",
        r"(?im)^\s*server:\s*\n\s*port:\s*([0-9]+)\s*$",
        r"(?im)\bPORT\s*=\s*([0-9]+)\b",
        r"(?im)--port\s+([0-9]+)\b",
        r"(?im)\bport\s*[:=]\s*([0-9]+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def _fastapi_app_module(root: Path, service_path: Path) -> str | None:
    for path in sorted(service_path.rglob("*.py")):
        text = _read_text(path)
        if "FastAPI(" not in text or "app" not in text:
            continue
        module_path = path.relative_to(root).with_suffix("").as_posix().replace("/", ".")
        return module_path
    return None


def _read_package_json(path: Path) -> dict:
    try:
        data = json.loads(_read_text(path))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _is_ignored(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(part in {".git", "__pycache__", ".pytest_cache"} for part in relative_parts)
