from __future__ import annotations

from k8s_deploy_agent.build_profile import BuildProfile
from k8s_deploy_agent.dockerfile_gate import evaluate_dockerfile_proposal_gate
from k8s_deploy_agent.redaction import find_secret_leaks


def render_dockerfile_proposal_validation(
    profiles: tuple[BuildProfile, ...],
    proposals: dict[str, str],
) -> str:
    lines = [
        "# Dockerfile Proposal Validation",
        "",
        "| Check | Status | Detail |",
        "|-------|--------|--------|",
        _check_row("Secret redaction", not find_secret_leaks(proposals), "proposal artifacts contain no secret-like values"),
        _check_row("Review-only output", _review_only_paths(proposals), "all artifacts are under dockerfile-proposals/"),
        _check_row("Confidence gate", _all_proposal_profiles_allowed(profiles, proposals), "proposal services passed BuildProfile gate"),
        "",
        "## Proposal Services",
        "",
        "| Service | App Type | Confidence | Gate | Detail |",
        "|---------|----------|------------|------|--------|",
    ]
    proposal_services = _proposal_services(proposals)
    if not proposal_services:
        lines.append("| - | - | - | - | no Dockerfile proposals generated |")
    else:
        profile_by_name = {profile.service_name: profile for profile in profiles}
        for service_name in proposal_services:
            profile = profile_by_name.get(service_name)
            if profile is None:
                lines.append(f"| {service_name} | - | - | blocked | missing BuildProfile |")
                continue
            gate = evaluate_dockerfile_proposal_gate(profile)
            detail = "-" if gate.allowed else "; ".join(gate.reasons)
            lines.append(
                f"| {service_name} | {profile.app_type} | {profile.confidence} | "
                f"{'pass' if gate.allowed else 'blocked'} | {detail} |"
            )
    lines.append("")
    return "\n".join(lines)


def _check_row(name: str, ok: bool, detail: str) -> str:
    return f"| {name} | {'pass' if ok else 'blocked'} | {detail} |"


def _review_only_paths(proposals: dict[str, str]) -> bool:
    return all(path.startswith("dockerfile-proposals/") for path in proposals)


def _all_proposal_profiles_allowed(profiles: tuple[BuildProfile, ...], proposals: dict[str, str]) -> bool:
    profile_by_name = {profile.service_name: profile for profile in profiles}
    for service_name in _proposal_services(proposals):
        profile = profile_by_name.get(service_name)
        if profile is None or not evaluate_dockerfile_proposal_gate(profile).allowed:
            return False
    return True


def _proposal_services(proposals: dict[str, str]) -> list[str]:
    services = []
    for path in proposals:
        parts = path.split("/")
        if len(parts) >= 3 and parts[0] == "dockerfile-proposals":
            services.append(parts[1])
    return sorted(set(services))
