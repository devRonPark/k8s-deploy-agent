#!/usr/bin/env python3
"""Create a run-scoped planning context for task decomposition."""

from __future__ import annotations

import argparse
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from tasklib import add_common_args, load_tasks, root_path


DEFAULT_PROPOSAL_DIR = ".harness/shared/planning"
DOCS = [
    ("PRD", "docs/PRD.md"),
    ("User Flow", "docs/UserFlow.md"),
    ("Design", "docs/DESIGN.md"),
    ("Architecture", "docs/Architecture.md"),
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def make_run_id() -> str:
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    return f"plan-{stamp}-{secrets.token_hex(3)}"


def document_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for label, path in DOCS:
        entries.append({"label": label, "path": path, "exists": (root / path).exists()})
    return entries


def task_entries(root: Path) -> list[dict[str, str]]:
    return [
        {"id": task.id, "title": task.title, "status": task.status, "section": task.section}
        for task in load_tasks(root)
    ]


def build_context(root: Path, request: str, proposal_dir: str, run_id: str | None = None) -> dict[str, Any]:
    actual_run_id = run_id or make_run_id()
    run_dir = Path(proposal_dir) / "runs" / actual_run_id
    return {
        "run_id": actual_run_id,
        "created_at": now_iso(),
        "request": request,
        "documents": document_entries(root),
        "existing_tasks": task_entries(root),
        "rules": {
            "task_decomposer": "agents/task-decomposer.md",
            "task_state_source": "tasks/index.json",
            "readable_plan": "Plans.md",
        },
        "outputs": {
            "run_dir": str(run_dir),
            "proposal": str(run_dir / "proposed-tasks.json"),
            "report": str(run_dir / "decomposition-report.md"),
        },
        "technical": {
            "schema_version": 1,
            "proposal_dir": proposal_dir,
        },
    }


def write_context(root: Path, context: dict[str, Any]) -> Path:
    run_dir = root / context["outputs"]["run_dir"]
    run_dir.mkdir(parents=True, exist_ok=True)
    context_path = run_dir / "context.json"
    context_path.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    latest_path = root / context["technical"]["proposal_dir"] / "latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest = {
        "run_id": context["run_id"],
        "updated_at": now_iso(),
        "context": str(Path(context["outputs"]["run_dir"]) / "context.json"),
        "proposal": context["outputs"]["proposal"],
        "report": context["outputs"]["report"],
    }
    latest_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return context_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a run-scoped planning context")
    add_common_args(parser)
    parser.add_argument("--request", required=True, help="user request to decompose")
    parser.add_argument("--run-id", help="optional stable run id")
    parser.add_argument("--proposal-dir", default=DEFAULT_PROPOSAL_DIR)
    args = parser.parse_args()

    root = root_path(args.root)
    try:
        context = build_context(root, args.request, args.proposal_dir, args.run_id)
        path = write_context(root, context)
    except Exception as exc:
        print(f"✗ {exc}")
        return 1

    print(f"✓ wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
