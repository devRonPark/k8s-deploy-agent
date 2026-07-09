from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from k8s_deploy_agent import __version__
from k8s_deploy_agent.analyzer import analyze_repository
from k8s_deploy_agent.config import load_demo_config
from k8s_deploy_agent.dockerfile_proposal import render_dockerfile_proposals, render_dockerignore_proposals
from k8s_deploy_agent.dockerfile_validation import render_dockerfile_proposal_validation
from k8s_deploy_agent.gitops import render_gitops_manifests
from k8s_deploy_agent.jenkinsfile import render_jenkinsfile
from k8s_deploy_agent.manifest_plan import build_workload_manifest_plans
from k8s_deploy_agent.manual_actions import render_manual_actions
from k8s_deploy_agent.redaction import assert_no_secret_values
from k8s_deploy_agent.report import render_repository_analysis
from k8s_deploy_agent.source_repo import clone_source_repository
from k8s_deploy_agent.ui import render_dry_run_dashboard
from k8s_deploy_agent.web import run_web_server

REPORT_PATH = ".agent/reports/repository-analysis.md"
MANUAL_ACTIONS_PATH = ".agent/reports/manual-actions.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="k8s-deploy-agent",
        description="Generate Jenkins CI and Rancher Fleet CD assets for a source repository.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the CLI version and exit.",
    )

    subparsers = parser.add_subparsers(dest="command")
    dry_run = subparsers.add_parser(
        "dry-run",
        help="Analyze a repository and generate all assets locally without pushing.",
    )
    dry_run.add_argument("--config", required=True, help="Path to demo inputs YAML.")
    dry_run.add_argument(
        "--repo",
        help=(
            "Path to a local source repository to analyze. "
            "If omitted, the repository is cloned from the config source_repo_url/source_branch."
        ),
    )
    dry_run.add_argument("--output", required=True, help="Directory to write generated assets into.")
    dry_run.add_argument("--image-tag", default="latest", help="Image tag used in generated manifests.")
    web = subparsers.add_parser(
        "web",
        help="Start the local operator console.",
    )
    web.add_argument("--host", default="127.0.0.1", help="Host interface for the local console.")
    web.add_argument("--port", type=int, default=8080, help="Port for the local console.")
    return parser


def run_dry_run(config_path: str, repo_path: str | None, output_dir: str, image_tag: str = "latest") -> list[str]:
    config = load_demo_config(config_path)
    return run_dry_run_with_config(config, repo_path, output_dir, image_tag=image_tag)


def run_dry_run_with_config(
    config,
    repo_path: str | None,
    output_dir: str,
    image_tag: str = "latest",
) -> list[str]:
    if repo_path:
        analysis = analyze_repository(repo_path)
    else:
        with tempfile.TemporaryDirectory(prefix="k8s-deploy-agent-") as work_dir:
            cloned_repo = clone_source_repository(config, work_dir)
            analysis = analyze_repository(cloned_repo)
            return _write_generated_assets(config, analysis, output_dir, image_tag)

    return _write_generated_assets(config, analysis, output_dir, image_tag)


def _write_generated_assets(
    config,
    analysis,
    output_dir: str,
    image_tag: str,
) -> list[str]:
    manifest_plan = build_workload_manifest_plans(config, analysis, image_tag)
    generated = {
        REPORT_PATH: render_repository_analysis(analysis),
        MANUAL_ACTIONS_PATH: render_manual_actions(manifest_plan, image_tag),
        "Jenkinsfile": render_jenkinsfile(config, analysis),
    }
    manifests = render_gitops_manifests(config, analysis, image_tag=image_tag)
    generated.update({f"gitops/{name}": content for name, content in manifests.items()})
    dockerfile_proposals = render_dockerfile_proposals(analysis.build_profiles)
    dockerignore_proposals = render_dockerignore_proposals(analysis.build_profiles)
    generated.update({f"dockerfile-proposals/{name}": content for name, content in dockerfile_proposals.items()})
    generated.update({f"dockerfile-proposals/{name}": content for name, content in dockerignore_proposals.items()})
    proposal_artifacts = {
        path: content
        for path, content in generated.items()
        if path.startswith("dockerfile-proposals/")
    }
    generated["dockerfile-proposals/VALIDATION.md"] = render_dockerfile_proposal_validation(
        analysis.build_profiles,
        proposal_artifacts,
    )
    generated_paths = sorted([*generated, "index.html"])
    generated["index.html"] = render_dry_run_dashboard(config, analysis, generated_paths, image_tag)

    assert_no_secret_values(generated)

    out = Path(output_dir)
    for relative_path, content in generated.items():
        target = out / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return sorted(generated)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"k8s-deploy-agent {__version__}")
        return 0

    if args.command == "dry-run":
        try:
            written = run_dry_run(args.config, args.repo, args.output, image_tag=args.image_tag)
        except ValueError as error:
            print(f"dry-run failed: {error}", file=sys.stderr)
            return 1
        print(f"dry-run complete: {len(written)} files written to {args.output}")
        for path in written:
            print(f"  {path}")
        return 0

    if args.command == "web":
        try:
            run_web_server(args.host, args.port)
        except OSError as error:
            print(f"web failed: {error}", file=sys.stderr)
            return 1
        return 0

    parser.print_help()
    return 0
