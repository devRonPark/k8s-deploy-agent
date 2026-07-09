from __future__ import annotations

from k8s_deploy_agent.manifest_plan import ManifestPlan

JENKINS_RUNTIME_IMAGE_TAG = "${BUILD_NUMBER}"

STATEFUL_DEPENDENCY_KINDS = ("postgres", "mariadb", "mysql", "redis", "mongodb")
EXTERNAL_DEPENDENCY_KINDS = ("smtp", "object_storage", "external_api")


def render_manual_actions(manifest_plan: ManifestPlan, image_tag: str) -> str:
    lines = ["# Manual Actions", ""]
    lines.extend(_skipped_manifests_section(manifest_plan))
    lines.extend(_unresolved_ports_section(manifest_plan))
    lines.extend(_secret_keys_section(manifest_plan))
    lines.extend(_dependency_section("Stateful Dependencies", manifest_plan, STATEFUL_DEPENDENCY_KINDS))
    lines.extend(_dependency_section("External Dependencies", manifest_plan, EXTERNAL_DEPENDENCY_KINDS))
    lines.extend(_external_exposure_section(manifest_plan))
    lines.extend(_image_tag_section(image_tag))
    return "\n".join(lines)


def _skipped_manifests_section(manifest_plan: ManifestPlan) -> list[str]:
    skipped = [workload for workload in manifest_plan.workloads if not workload.confirmed]
    lines = ["## Skipped Manifests", "", "| Service | Reason |", "|---------|--------|"]
    if not skipped:
        lines.append("| - | No manifests were skipped. |")
    else:
        for workload in skipped:
            reason = "; ".join(workload.unresolved_questions) or "not confirmed"
            lines.append(f"| {workload.service_name} | {reason} |")
    lines.append("")
    return lines


def _unresolved_ports_section(manifest_plan: ManifestPlan) -> list[str]:
    port_questions = [question for question in manifest_plan.unresolved_questions if "port" in question]
    lines = ["## Unresolved / Conflicting Ports", ""]
    if not port_questions:
        lines.append("No unresolved or conflicting ports.")
    else:
        lines.extend(f"- {question}" for question in port_questions)
    lines.append("")
    return lines


def _secret_keys_section(manifest_plan: ManifestPlan) -> list[str]:
    rows = [
        (workload.service_name, plan.key)
        for workload in manifest_plan.workloads
        for plan in workload.env_plans
        if plan.category == "secret"
    ]
    lines = ["## Required Secret Keys", "", "| Service | Key |", "|---------|-----|"]
    if not rows:
        lines.append("| - | No secret keys detected. |")
    else:
        lines.extend(f"| {service_name} | {key} |" for service_name, key in rows)
    lines.append("")
    return lines


def _dependency_section(title: str, manifest_plan: ManifestPlan, kinds: tuple[str, ...]) -> list[str]:
    rows = [
        (workload.service_name, plan.name, plan.action)
        for workload in manifest_plan.workloads
        for plan in workload.dependency_plans
        if plan.kind in kinds
    ]
    lines = [f"## {title}", "", "| Service | Dependency | Action |", "|---------|------------|--------|"]
    if not rows:
        lines.append(f"| - | No {title.lower()} detected. | - |")
    else:
        lines.extend(f"| {service_name} | {name} | {action} |" for service_name, name, action in rows)
    lines.append("")
    return lines


def _external_exposure_section(manifest_plan: ManifestPlan) -> list[str]:
    exposed = [
        workload
        for workload in manifest_plan.confirmed
        if workload.container_port is not None and workload.container_port.kind == "reverse_proxy"
    ]
    lines = ["## External Exposure Note", ""]
    if not exposed:
        lines.append("No reverse-proxy-based external exposure detected among confirmed services.")
    else:
        lines.append(
            "The following confirmed services expose a port via a reverse proxy "
            "(e.g. nginx) and are likely intended for external access — review "
            "Ingress/TLS configuration before deploying:"
        )
        lines.append("")
        lines.extend(
            f"- {workload.service_name} (port {workload.container_port.value}, "
            f"evidence: {workload.container_port.evidence_path})"
            for workload in exposed
        )
    lines.append("")
    return lines


def _image_tag_section(image_tag: str) -> list[str]:
    return [
        "## Image Tag Note",
        "",
        "| Context | Image Tag |",
        "|---------|-----------|",
        f"| GitOps preview (this dry-run) | {image_tag} |",
        f"| Jenkins runtime pipeline | {JENKINS_RUNTIME_IMAGE_TAG} |",
        "",
        "These differ intentionally: the GitOps preview uses the `--image-tag` value "
        "for local review, while the Jenkins pipeline always tags images with the "
        "Jenkins build number at push time.",
    ]
