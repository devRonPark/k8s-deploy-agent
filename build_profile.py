from __future__ import annotations

from dataclasses import dataclass


Confidence = str


@dataclass(frozen=True)
class ProfileEvidence:
    field: str
    path: str
    value: str
    reason: str


@dataclass(frozen=True)
class BuildProfile:
    service_name: str
    service_path: str
    app_type: str
    framework: str | None = None
    dependency_files: tuple[str, ...] = ()
    lockfiles: tuple[str, ...] = ()
    build_tool: str | None = None
    build_command: str | None = None
    runtime_command: str | None = None
    build_output: str | None = None
    docker_context: str | None = None
    dockerfile_existing: str | None = None
    ignore_candidates: tuple[str, ...] = ()
    exposed_port: int | None = None
    health_endpoint: str | None = None
    confidence: Confidence = "low"
    evidence: tuple[ProfileEvidence, ...] = ()
    unresolved_questions: tuple[str, ...] = ()

    @property
    def confirmed(self) -> bool:
        return self.confidence == "confirmed" and not self.unresolved_questions
