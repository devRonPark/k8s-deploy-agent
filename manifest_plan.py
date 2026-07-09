from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from k8s_deploy_agent.redaction import is_public_config_key, is_secret_key


IGNORED_DIRS = {
    ".git",
    ".gradle",
    ".next",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "venv",
}


@dataclass(frozen=True)
class PortCandidate:
    value: int
    kind: str
    source: str
    confidence: str
    evidence_path: str
    reason: str


@dataclass(frozen=True)
class EnvVarPlan:
    key: str
    category: str
    evidence_path: str
    reason: str


@dataclass(frozen=True)
class DependencyPlan:
    name: str
    kind: str
    evidence_path: str
    reason: str
    action: str


def collect_port_candidates(
    repo_root: str | Path,
    service_path: str | Path,
    *,
    runtime_command: str | None = None,
    app_type: str | None = None,
) -> tuple[PortCandidate, ...]:
    root = Path(repo_root).resolve()
    service = _resolve_service_path(root, service_path)
    candidates: list[PortCandidate] = []

    candidates.extend(_dockerfile_expose_candidates(root, service))
    candidates.extend(_compose_candidates(root, service))
    candidates.extend(
        _runtime_command_candidates(runtime_command, "runtime_command", "runtime command port detected")
    )
    candidates.extend(_nginx_candidates(root, service))
    candidates.extend(_package_script_candidates(root, service))
    candidates.extend(_config_candidates(root, service, app_type))

    return tuple(_dedupe_candidates(candidates))


def collect_env_var_plans(
    repo_root: str | Path,
    service_path: str | Path,
    *,
    app_type: str | None = None,
) -> tuple[EnvVarPlan, ...]:
    root = Path(repo_root).resolve()
    service = _resolve_service_path(root, service_path)
    plans: list[EnvVarPlan] = []

    plans.extend(_env_file_plans(root, root))
    if service != root:
        plans.extend(_env_file_plans(root, service))
    plans.extend(_compose_env_plans(root, service))
    plans.extend(_python_env_plans(root, service) if app_type in (None, "python") else [])
    plans.extend(_node_env_plans(root, service) if app_type in (None, "node") else [])
    plans.extend(_java_env_plans(root, service) if app_type in (None, "java") else [])

    return tuple(_dedupe_env_plans(plans))


def collect_dependency_plans(
    repo_root: str | Path,
    service_path: str | Path,
    *,
    app_type: str | None = None,
) -> tuple[DependencyPlan, ...]:
    root = Path(repo_root).resolve()
    service = _resolve_service_path(root, service_path)
    env_plans = collect_env_var_plans(root, service, app_type=app_type)
    dependencies: list[DependencyPlan] = []

    for plan in env_plans:
        dependency = _dependency_from_key(plan.key, plan.evidence_path)
        if dependency:
            dependencies.append(dependency)

    dependencies.extend(_compose_image_dependencies(root, service))
    return tuple(_dedupe_dependency_plans(dependencies))


def _resolve_service_path(root: Path, service_path: str | Path) -> Path:
    path = Path(service_path)
    if path.is_absolute():
        return path.resolve()
    if path.as_posix() == ".":
        return root
    return (root / path).resolve()


def _env_file_plans(root: Path, base_path: Path) -> list[EnvVarPlan]:
    plans: list[EnvVarPlan] = []
    for name in (".env.example", ".env"):
        path = base_path / name
        text = _read_text(path)
        if not text:
            continue
        for key in _env_keys_from_assignment_text(text):
            plans.append(_env_plan(key, _relative_path(root, path), "environment file key detected"))
    return plans


def _compose_env_plans(root: Path, service: Path) -> list[EnvVarPlan]:
    plans: list[EnvVarPlan] = []
    for compose_file in _compose_files(root, service):
        text = _read_text(compose_file)
        if not text:
            continue
        for block in _compose_blocks_for_service(text, service.name):
            for key in _compose_environment_keys(block):
                plans.append(_env_plan(key, _relative_path(root, compose_file), "docker-compose environment key detected"))
    return plans


def _python_env_plans(root: Path, service: Path) -> list[EnvVarPlan]:
    plans: list[EnvVarPlan] = []
    for path in _service_files(service, ("*.py",)):
        text = _read_text(path)
        for key in _python_env_keys(text):
            plans.append(_env_plan(key, _relative_path(root, path), "Python environment key detected"))
    return plans


def _node_env_plans(root: Path, service: Path) -> list[EnvVarPlan]:
    plans: list[EnvVarPlan] = []
    for path in _service_files(service, ("*.js", "*.jsx", "*.ts", "*.tsx")):
        text = _read_text(path)
        for key in _node_env_keys(text):
            plans.append(_env_plan(key, _relative_path(root, path), "Node environment key detected"))
    return plans


def _java_env_plans(root: Path, service: Path) -> list[EnvVarPlan]:
    plans: list[EnvVarPlan] = []
    for path in _service_files(service, ("*.java", "application.properties", "application.yml", "application.yaml")):
        text = _read_text(path)
        for key in _java_env_keys(text):
            plans.append(_env_plan(key, _relative_path(root, path), "Java/config environment key detected"))
    return plans


def _env_plan(key: str, evidence_path: str, reason: str) -> EnvVarPlan:
    return EnvVarPlan(
        key=key,
        category=_env_category(key),
        evidence_path=evidence_path,
        reason=reason,
    )


def _env_category(key: str) -> str:
    if is_public_config_key(key):
        return "public_config"
    if is_secret_key(key):
        return "secret"
    if _dependency_kind_from_key(key) is not None:
        return "dependency"
    return "configmap"


def _env_keys_from_assignment_text(text: str) -> list[str]:
    keys: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if _is_env_key(key):
            keys.append(key)
    return keys


def _python_env_keys(text: str) -> list[str]:
    keys: list[str] = []
    patterns = (
        r"""os\.getenv\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']""",
        r"""os\.environ\[\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\]""",
        r"(?m)^\s{4,}([A-Z][A-Z0-9_]*)\s*:\s*[^=\n]+",
    )
    for pattern in patterns:
        keys.extend(match.group(1) for match in re.finditer(pattern, text))
    return keys


def _node_env_keys(text: str) -> list[str]:
    keys: list[str] = []
    patterns = (
        r"\bprocess\.env\.([A-Za-z_][A-Za-z0-9_]*)\b",
        r"\bimport\.meta\.env\.([A-Za-z_][A-Za-z0-9_]*)\b",
    )
    for pattern in patterns:
        keys.extend(match.group(1) for match in re.finditer(pattern, text))
    return keys


def _java_env_keys(text: str) -> list[str]:
    keys: list[str] = []
    patterns = (
        r"""System\.getenv\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\)""",
        r"\$\{([A-Za-z_][A-Za-z0-9_]*)",
    )
    for pattern in patterns:
        keys.extend(match.group(1) for match in re.finditer(pattern, text))
    return keys


def _compose_environment_keys(block: list[str]) -> list[str]:
    keys: list[str] = []
    index = 0
    while index < len(block):
        line = block[index]
        if _mapping_key(line) != "environment":
            index += 1
            continue

        inline = line.split(":", 1)[1].strip()
        if inline:
            keys.extend(_keys_from_inline_environment(inline))
            index += 1
            continue

        key_indent = _indent(line)
        index += 1
        while index < len(block):
            item_line = block[index]
            if not item_line.strip() or item_line.lstrip().startswith("#"):
                index += 1
                continue
            if _indent(item_line) <= key_indent:
                break
            stripped = item_line.strip()
            if stripped.startswith("-"):
                raw = stripped[1:].strip()
                key = raw.split("=", 1)[0].strip()
            else:
                key = _mapping_key(stripped) or ""
            if _is_env_key(key):
                keys.append(key)
            index += 1
    return keys


def _keys_from_inline_environment(value: str) -> list[str]:
    stripped = value.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return [
            part.split("=", 1)[0].strip().strip("'\"")
            for part in stripped[1:-1].split(",")
            if _is_env_key(part.split("=", 1)[0].strip().strip("'\""))
        ]
    if stripped.startswith("{") and stripped.endswith("}"):
        keys: list[str] = []
        for part in stripped[1:-1].split(","):
            key = part.split(":", 1)[0].strip().strip("'\"")
            if _is_env_key(key):
                keys.append(key)
        return keys
    return []


def _is_env_key(key: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key))


def _dependency_from_key(key: str, evidence_path: str) -> DependencyPlan | None:
    kind = _dependency_kind_from_key(key)
    if kind is None:
        return None
    name = "external_api" if kind == "external_api" else kind
    return DependencyPlan(
        name=name,
        kind=kind,
        evidence_path=evidence_path,
        reason=f"{_dependency_label(kind)} dependency detected from {key}",
        action="review-required" if kind == "external_api" else "manual-required",
    )


def _dependency_kind_from_key(key: str) -> str | None:
    normalized = key.upper()
    if "POSTGRES" in normalized or normalized in {"DATABASE_URL", "DATABASE_DIRECT_URL"}:
        return "postgres"
    if "MARIADB" in normalized:
        return "mariadb"
    if "MYSQL" in normalized:
        return "mysql"
    if "REDIS" in normalized:
        return "redis"
    if "MONGODB" in normalized or "MONGO_" in normalized:
        return "mongodb"
    if "SMTP" in normalized:
        return "smtp"
    if normalized.startswith("S3_") or normalized.startswith("AWS_") or "OBJECT_STORAGE" in normalized or "MINIO" in normalized:
        return "object_storage"
    if "OPENAI" in normalized or "AZURE_OPENAI" in normalized:
        return "external_api"
    return None


def _dependency_label(kind: str) -> str:
    return {
        "postgres": "Postgres",
        "mariadb": "MariaDB",
        "mysql": "MySQL",
        "redis": "Redis",
        "mongodb": "MongoDB",
        "smtp": "SMTP",
        "object_storage": "Object storage",
        "external_api": "External API",
    }.get(kind, kind)


def _compose_image_dependencies(root: Path, service: Path) -> list[DependencyPlan]:
    dependencies: list[DependencyPlan] = []
    for compose_file in _compose_files(root, service):
        text = _read_text(compose_file)
        if not text:
            continue
        for kind in _dependency_kinds_from_compose_images(text):
            dependencies.append(
                DependencyPlan(
                    name="external_api" if kind == "external_api" else kind,
                    kind=kind,
                    evidence_path=_relative_path(root, compose_file),
                    reason=f"{_dependency_label(kind)} dependency detected from docker-compose service image",
                    action="manual-required",
                )
            )
    return dependencies


def _dependency_kinds_from_compose_images(text: str) -> list[str]:
    kinds: list[str] = []
    for match in re.finditer(r"(?im)^\s*image\s*:\s*([^\s#]+)", text):
        image = match.group(1).lower()
        if "postgres" in image:
            kinds.append("postgres")
        elif "mariadb" in image:
            kinds.append("mariadb")
        elif "mysql" in image:
            kinds.append("mysql")
        elif "redis" in image:
            kinds.append("redis")
        elif "mongo" in image:
            kinds.append("mongodb")
    return kinds


def _dockerfile_expose_candidates(root: Path, service: Path) -> list[PortCandidate]:
    dockerfile = service / "Dockerfile"
    text = _read_text(dockerfile)
    if not text:
        return []

    candidates: list[PortCandidate] = []
    for match in re.finditer(r"(?im)^\s*EXPOSE\s+(.+)$", text):
        for token in match.group(1).split():
            port = _first_port(token)
            if port is None:
                continue
            candidates.append(
                PortCandidate(
                    value=port,
                    kind="container",
                    source="dockerfile_expose",
                    confidence="confirmed",
                    evidence_path=_relative_path(root, dockerfile),
                    reason="Dockerfile EXPOSE detected",
                )
            )
    return candidates


def _compose_candidates(root: Path, service: Path) -> list[PortCandidate]:
    candidates: list[PortCandidate] = []
    for compose_file in _compose_files(root, service):
        text = _read_text(compose_file)
        if not text:
            continue
        for block in _compose_blocks_for_service(text, service.name):
            candidates.extend(_compose_port_candidates(root, compose_file, block))
            candidates.extend(_compose_expose_candidates(root, compose_file, block))
            candidates.extend(_compose_command_candidates(root, compose_file, block))
    return candidates


def _compose_files(root: Path, service: Path) -> list[Path]:
    candidates = [
        root / "docker-compose.yml",
        root / "docker-compose.yaml",
        service / "docker-compose.yml",
        service / "docker-compose.yaml",
    ]
    found: list[Path] = []
    for path in candidates:
        if path.is_file() and path not in found:
            found.append(path)
    return found


def _compose_blocks_for_service(text: str, service_name: str) -> list[list[str]]:
    lines = text.splitlines()
    services_index = _find_mapping_line(lines, "services")
    if services_index is None:
        return [lines]

    blocks: list[list[str]] = []
    services_indent = _indent(lines[services_index])
    index = services_index + 1
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        indent = _indent(line)
        if indent <= services_indent:
            break
        key = _mapping_key(line)
        if key is None:
            index += 1
            continue

        block_start = index
        index += 1
        while index < len(lines):
            next_line = lines[index]
            if next_line.strip() and not next_line.lstrip().startswith("#"):
                next_indent = _indent(next_line)
                if next_indent <= services_indent:
                    break
                if next_indent == indent and _mapping_key(next_line) is not None:
                    break
            index += 1
        if key == service_name:
            blocks.append(lines[block_start:index])
    return blocks


def _compose_port_candidates(root: Path, compose_file: Path, block: list[str]) -> list[PortCandidate]:
    candidates: list[PortCandidate] = []
    for raw_value in _compose_list_values(block, "ports"):
        mapping = _parse_compose_port(raw_value)
        if mapping.container_port is None:
            continue
        evidence = _relative_path(root, compose_file)
        if mapping.host_port is not None:
            candidates.append(
                PortCandidate(
                    value=mapping.host_port,
                    kind="host",
                    source="compose_ports",
                    confidence="confirmed",
                    evidence_path=evidence,
                    reason="docker-compose host port detected",
                )
            )
        candidates.append(
            PortCandidate(
                value=mapping.container_port,
                kind="container",
                source="compose_ports",
                confidence="confirmed",
                evidence_path=evidence,
                reason="docker-compose container port detected",
            )
        )
    return candidates


def _compose_expose_candidates(root: Path, compose_file: Path, block: list[str]) -> list[PortCandidate]:
    candidates: list[PortCandidate] = []
    for raw_value in _compose_list_values(block, "expose"):
        port = _first_port(raw_value)
        if port is None:
            continue
        candidates.append(
            PortCandidate(
                value=port,
                kind="container",
                source="compose_expose",
                confidence="confirmed",
                evidence_path=_relative_path(root, compose_file),
                reason="docker-compose expose port detected",
            )
        )
    return candidates


def _compose_command_candidates(root: Path, compose_file: Path, block: list[str]) -> list[PortCandidate]:
    command = _compose_scalar_value(block, "command")
    if command is None:
        return []
    return [
        PortCandidate(
            value=port,
            kind="container",
            source="runtime_command",
            confidence="confirmed",
            evidence_path=_relative_path(root, compose_file),
            reason="docker-compose service command port detected",
        )
        for port in _ports_from_command(command)
    ]


@dataclass(frozen=True)
class _ComposePortMapping:
    host_port: int | None
    container_port: int | None


def _parse_compose_port(raw_value: str) -> _ComposePortMapping:
    value = _strip_scalar(raw_value)
    value = value.split("/", 1)[0]
    parts = value.split(":")
    numeric_parts = [_first_port(part) for part in parts]
    numeric = [port for port in numeric_parts if port is not None]
    if not numeric:
        return _ComposePortMapping(host_port=None, container_port=None)
    if len(numeric) == 1:
        return _ComposePortMapping(host_port=None, container_port=numeric[0])
    return _ComposePortMapping(host_port=numeric[-2], container_port=numeric[-1])


def _nginx_candidates(root: Path, service: Path) -> list[PortCandidate]:
    candidates: list[PortCandidate] = []
    for path in _service_files(service, ("nginx.conf",)):
        text = _read_text(path)
        for match in re.finditer(r"(?im)\blisten\s+(?:[0-9.]+:)?([0-9]+)\b", text):
            candidates.append(
                PortCandidate(
                    value=int(match.group(1)),
                    kind="reverse_proxy",
                    source="nginx_listen",
                    confidence="confirmed",
                    evidence_path=_relative_path(root, path),
                    reason="nginx listen port detected",
                )
            )
    return candidates


def _package_script_candidates(root: Path, service: Path) -> list[PortCandidate]:
    package_json_path = service / "package.json"
    package_json = _read_package_json(package_json_path)
    scripts = package_json.get("scripts", {})
    if not isinstance(scripts, dict):
        return []

    candidates: list[PortCandidate] = []
    for script_name, command in scripts.items():
        if not isinstance(command, str):
            continue
        for port in _ports_from_command(command):
            is_dev = _is_dev_script(script_name, command)
            candidates.append(
                PortCandidate(
                    value=port,
                    kind="dev_server" if is_dev else "container",
                    source="package_script",
                    confidence="inferred" if is_dev else "confirmed",
                    evidence_path=_relative_path(root, package_json_path),
                    reason=f"package.json scripts.{script_name} port detected",
                )
            )
    return candidates


def _config_candidates(root: Path, service: Path, app_type: str | None) -> list[PortCandidate]:
    candidates: list[PortCandidate] = []
    candidates.extend(_generic_config_candidates(root, service))
    candidates.extend(_python_config_candidates(root, service) if app_type in (None, "python") else [])
    candidates.extend(_vite_config_candidates(root, service) if app_type in (None, "node") else [])
    return candidates


def _generic_config_candidates(root: Path, service: Path) -> list[PortCandidate]:
    relative_names = (
        ".env",
        ".env.example",
        "application.properties",
        "application.yml",
        "application.yaml",
        "config.yml",
        "config.yaml",
    )
    candidates: list[PortCandidate] = []
    for path in (service / name for name in relative_names):
        text = _read_text(path)
        if not text:
            continue
        for port in _ports_from_config_text(text):
            candidates.append(
                PortCandidate(
                    value=port,
                    kind="config",
                    source="app_config",
                    confidence="confirmed",
                    evidence_path=_relative_path(root, path),
                    reason="application config port detected",
                )
            )
    return candidates


def _python_config_candidates(root: Path, service: Path) -> list[PortCandidate]:
    candidates: list[PortCandidate] = []
    for path in _service_files(service, ("*.py",)):
        text = _read_text(path)
        for match in re.finditer(r"(?im)\bport\s*=\s*([0-9]+)\b", text):
            candidates.append(
                PortCandidate(
                    value=int(match.group(1)),
                    kind="config",
                    source="app_config",
                    confidence="confirmed",
                    evidence_path=_relative_path(root, path),
                    reason="Python explicit port detected",
                )
            )
    return candidates


def _vite_config_candidates(root: Path, service: Path) -> list[PortCandidate]:
    candidates: list[PortCandidate] = []
    for path in (service / "vite.config.js", service / "vite.config.ts"):
        text = _read_text(path)
        if not text:
            continue
        for match in re.finditer(r"(?is)\bserver\s*:\s*\{[^}]*\bport\s*:\s*([0-9]+)", text):
            candidates.append(
                PortCandidate(
                    value=int(match.group(1)),
                    kind="dev_server",
                    source="app_config",
                    confidence="inferred",
                    evidence_path=_relative_path(root, path),
                    reason="Vite dev server port detected",
                )
            )
    return candidates


def _runtime_command_candidates(command: str | None, evidence_path: str, reason: str) -> list[PortCandidate]:
    if not command:
        return []
    return [
        PortCandidate(
            value=port,
            kind="container",
            source="runtime_command",
            confidence="confirmed",
            evidence_path=evidence_path,
            reason=reason,
        )
        for port in _ports_from_command(command)
    ]


def _ports_from_command(command: str) -> list[int]:
    ports: list[int] = []
    patterns = (
        r"(?im)(?:^|\s)--port(?:=|\s+)([0-9]+)\b",
        r"(?im)(?:^|\s)-p(?:=|\s+)([0-9]+)\b",
        r"(?im)\bport\s*=\s*([0-9]+)\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, command):
            ports.append(int(match.group(1)))
    return ports


def _ports_from_config_text(text: str) -> list[int]:
    ports: list[int] = []
    patterns = (
        r"(?im)^\s*PORT\s*=\s*([0-9]+)\s*$",
        r"(?im)^\s*server\.port\s*=\s*([0-9]+)\s*$",
        r"(?im)^\s*server:\s*\n\s*port:\s*([0-9]+)\s*$",
        r"(?im)\bPORT\s*:\s*([0-9]+)\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            ports.append(int(match.group(1)))
    return ports


def _compose_list_values(block: list[str], key: str) -> list[str]:
    values: list[str] = []
    index = 0
    while index < len(block):
        line = block[index]
        if _mapping_key(line) != key:
            index += 1
            continue

        inline = line.split(":", 1)[1].strip()
        if inline:
            values.extend(_parse_inline_list(inline))
            index += 1
            continue

        key_indent = _indent(line)
        index += 1
        while index < len(block):
            item_line = block[index]
            if not item_line.strip() or item_line.lstrip().startswith("#"):
                index += 1
                continue
            if _indent(item_line) <= key_indent:
                break
            stripped = item_line.strip()
            if not stripped.startswith("-"):
                index += 1
                continue
            values.append(stripped[1:].strip())
            index += 1
    return values


def _compose_scalar_value(block: list[str], key: str) -> str | None:
    for line in block:
        if _mapping_key(line) != key:
            continue
        value = line.split(":", 1)[1].strip()
        return _strip_scalar(value) if value else None
    return None


def _parse_inline_list(value: str) -> list[str]:
    stripped = value.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return [_strip_scalar(stripped)]
    inner = stripped[1:-1].strip()
    if not inner:
        return []
    return [_strip_scalar(part.strip()) for part in inner.split(",")]


def _find_mapping_line(lines: list[str], key: str) -> int | None:
    for index, line in enumerate(lines):
        if _mapping_key(line) == key:
            return index
    return None


def _mapping_key(line: str) -> str | None:
    match = re.match(r"^\s*([A-Za-z0-9_.-]+)\s*:", line)
    return match.group(1) if match else None


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_dev_script(script_name: str, command: str) -> bool:
    normalized_name = script_name.lower()
    normalized_command = command.lower()
    if normalized_name in {"dev", "develop", "development"}:
        return True
    return "vite " in normalized_command and normalized_name != "start"


def _service_files(service: Path, patterns: tuple[str, ...]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        if any(char in pattern for char in "*?[]"):
            paths.extend(path for path in service.rglob(pattern) if path.is_file() and not _is_ignored(path, service))
        else:
            path = service / pattern
            if path.is_file():
                paths.append(path)
    return sorted(paths)


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


def _strip_scalar(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith(("'", '"')) and stripped.endswith(("'", '"')) and len(stripped) >= 2:
        return stripped[1:-1]
    return stripped


def _first_port(value: str) -> int | None:
    match = re.search(r"\b([0-9]{1,5})\b", _strip_scalar(value))
    if not match:
        return None
    port = int(match.group(1))
    if port < 1 or port > 65535:
        return None
    return port


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _is_ignored(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    return any(part in IGNORED_DIRS for part in parts)


def _dedupe_candidates(candidates: list[PortCandidate]) -> list[PortCandidate]:
    deduped: list[PortCandidate] = []
    seen: set[tuple[int, str, str, str, str]] = set()
    for candidate in candidates:
        key = (
            candidate.value,
            candidate.kind,
            candidate.source,
            candidate.confidence,
            candidate.evidence_path,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _dedupe_env_plans(plans: list[EnvVarPlan]) -> list[EnvVarPlan]:
    deduped: list[EnvVarPlan] = []
    seen: set[str] = set()
    for plan in plans:
        if plan.key in seen:
            continue
        seen.add(plan.key)
        deduped.append(plan)
    return deduped


def _dedupe_dependency_plans(plans: list[DependencyPlan]) -> list[DependencyPlan]:
    deduped: list[DependencyPlan] = []
    seen: set[str] = set()
    for plan in plans:
        if plan.name in seen:
            continue
        seen.add(plan.name)
        deduped.append(plan)
    return deduped
