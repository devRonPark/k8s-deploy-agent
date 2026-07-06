from __future__ import annotations

from dataclasses import dataclass

from k8s_deploy_agent.build_profile import BuildProfile


SUPPORTED_APP_TYPES = frozenset({"python", "node", "java", "go"})


@dataclass(frozen=True)
class DockerfileProposalGate:
    allowed: bool
    reasons: tuple[str, ...] = ()


def evaluate_dockerfile_proposal_gate(profile: BuildProfile) -> DockerfileProposalGate:
    reasons: list[str] = []

    if profile.app_type not in SUPPORTED_APP_TYPES:
        reasons.append(f"unsupported app type: {profile.app_type}")
    if profile.confidence == "low":
        reasons.append("profile confidence is low")
    if profile.unresolved_questions:
        reasons.extend(profile.unresolved_questions)
    if not profile.service_path:
        reasons.append("service path is not confirmed")
    if not profile.dependency_files:
        reasons.append("dependency files are not confirmed")
    if not profile.build_tool:
        reasons.append("build tool is not confirmed")
    if not profile.runtime_command:
        reasons.append("runtime command is not confirmed")
    if profile.exposed_port is None:
        reasons.append("exposed port is not confirmed")

    return DockerfileProposalGate(allowed=not reasons, reasons=tuple(dict.fromkeys(reasons)))
