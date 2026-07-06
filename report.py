from __future__ import annotations

from pathlib import Path

from k8s_deploy_agent.analyzer import RepositoryAnalysis, ServiceCandidate


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
