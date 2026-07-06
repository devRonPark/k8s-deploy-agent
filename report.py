from __future__ import annotations

from pathlib import Path

from k8s_deploy_agent.analyzer import RepositoryAnalysis, ServiceCandidate
from k8s_deploy_agent.build_profile import BuildProfile


def render_repository_analysis(analysis: RepositoryAnalysis) -> str:
    lines = [
        "# Repository Analysis",
        "",
        f"Root: `{analysis.root}`",
        "",
        "## Services",
        "",
        "| Service | Stack | Path | Dockerfile |",
        "|---------|-------|------|------------|",
    ]

    if analysis.services:
        lines.extend(_service_row(analysis, service) for service in analysis.services)
    else:
        lines.append("| - | - | - | - |")

    lines.extend(_build_profile_section(analysis))

    lines.extend(
        [
            "",
            "## File Tree Summary",
            "",
            f"Files scanned: {len(analysis.file_tree)}",
            "",
        ]
    )
    return "\n".join(lines)


def write_repository_analysis_report(analysis: RepositoryAnalysis, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_repository_analysis(analysis), encoding="utf-8")
    return path


def _service_row(analysis: RepositoryAnalysis, service: ServiceCandidate) -> str:
    service_path = service.path.relative_to(analysis.root).as_posix()
    dockerfile = "-"
    if service.dockerfile:
        dockerfile = service.dockerfile.relative_to(analysis.root).as_posix()
    return f"| {service.name} | {service.stack} | {service_path} | {dockerfile} |"


def _build_profile_section(analysis: RepositoryAnalysis) -> list[str]:
    lines = [
        "",
        "## Build Profiles",
        "",
        "| Service | App Type | Build Tool | Runtime Command | Port | Confidence | Unresolved |",
        "|---------|----------|------------|-----------------|------|------------|------------|",
    ]
    if not analysis.build_profiles:
        lines.append("| - | - | - | - | - | - | - |")
        return lines

    for profile in analysis.build_profiles:
        lines.append(_build_profile_row(profile))

    lines.extend(["", "### Build Profile Evidence", ""])
    for profile in analysis.build_profiles:
        lines.extend(_build_profile_evidence(profile))
    return lines


def _build_profile_row(profile: BuildProfile) -> str:
    runtime_command = profile.runtime_command or "-"
    port = str(profile.exposed_port) if profile.exposed_port is not None else "-"
    unresolved = "; ".join(profile.unresolved_questions) if profile.unresolved_questions else "-"
    return (
        f"| {profile.service_name} | {profile.app_type} | {profile.build_tool or '-'} | "
        f"{runtime_command} | {port} | {profile.confidence} | {unresolved} |"
    )


def _build_profile_evidence(profile: BuildProfile) -> list[str]:
    lines = [
        f"#### {profile.service_name}",
        "",
        "| Field | Path | Value | Reason |",
        "|-------|------|-------|--------|",
    ]
    if not profile.evidence:
        lines.append("| - | - | - | - |")
    else:
        for evidence in profile.evidence:
            lines.append(f"| {evidence.field} | {evidence.path} | {evidence.value} | {evidence.reason} |")
    lines.append("")
    return lines
