from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
    return RepositoryAnalysis(root=root_path, file_tree=file_tree, services=services)


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


def _is_ignored(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(part in {".git", "__pycache__", ".pytest_cache"} for part in relative_parts)
