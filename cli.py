from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from k8s_deploy_agent import __version__
from k8s_deploy_agent.analyzer import analyze_repository
from k8s_deploy_agent.config import load_demo_config
from k8s_deploy_agent.gitops import render_gitops_manifests
from k8s_deploy_agent.jenkinsfile import render_jenkinsfile
from k8s_deploy_agent.redaction import assert_no_secret_values
from k8s_deploy_agent.report import render_repository_analysis

REPORT_PATH = ".agent/reports/repository-analysis.md"


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
    dry_run.add_argument("--repo", required=True, help="Path to the source repository to analyze.")
    dry_run.add_argument("--output", required=True, help="Directory to write generated assets into.")
    dry_run.add_argument("--image-tag", default="latest", help="Image tag used in generated manifests.")
    return parser


def run_dry_run(config_path: str, repo_path: str, output_dir: str, image_tag: str = "latest") -> list[str]:
    config = load_demo_config(config_path)
    analysis = analyze_repository(repo_path)

    generated = {
        REPORT_PATH: render_repository_analysis(analysis),
        "Jenkinsfile": render_jenkinsfile(config, analysis),
    }
    manifests = render_gitops_manifests(config, analysis, image_tag=image_tag)
    generated.update({f"gitops/{name}": content for name, content in manifests.items()})

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

    parser.print_help()
    return 0
