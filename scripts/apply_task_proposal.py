#!/usr/bin/env python3
"""Apply a validated task proposal to tasks/index.json and refresh Plans.md."""

from __future__ import annotations

import argparse
from pathlib import Path

from tasklib import (
    add_common_args,
    load_task_document,
    load_tasks,
    plans_path,
    render_plans,
    root_path,
    validate_tasks,
    write_task_document,
)
from validate_task_proposal import load_proposed_tasks, validate_proposal


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply task proposal JSON")
    add_common_args(parser)
    parser.add_argument("--proposal", required=True, help="path to proposed-tasks.json")
    args = parser.parse_args()

    root = root_path(args.root)
    proposal_path = Path(args.proposal)
    if not proposal_path.is_absolute():
        proposal_path = root / proposal_path

    try:
        document = load_task_document(root)
        existing = load_tasks(root)
        proposed = load_proposed_tasks(proposal_path)
        errors = validate_proposal(existing, proposed)
        if errors:
            raise ValueError("\n".join(errors))

        combined = existing + proposed
        combined_errors = validate_tasks(combined)
        if combined_errors:
            raise ValueError("\n".join(combined_errors))

        write_task_document(root, combined, document)
        plans_path(root).write_text(render_plans(root, combined), encoding="utf-8")
    except Exception as exc:
        print(f"✗ {exc}")
        return 1

    print(f"✓ applied {len(proposed)} proposed tasks")
    print(f"✓ wrote {plans_path(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
