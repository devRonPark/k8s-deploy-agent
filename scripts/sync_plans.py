#!/usr/bin/env python3
"""Render Plans.md from tasks/index.json."""

from __future__ import annotations

import argparse
import sys

from tasklib import add_common_args, ensure_valid_tasks, plans_path, render_plans, root_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Plans.md from tasks/index.json")
    add_common_args(parser)
    parser.add_argument("--check", action="store_true", help="fail if Plans.md is not in sync")
    parser.add_argument("--task-id", help="accepted for command symmetry; sync still renders all tasks")
    args = parser.parse_args()

    root = root_path(args.root)
    try:
        tasks = ensure_valid_tasks(root)
        rendered = render_plans(root, tasks)
    except Exception as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1

    path = plans_path(root)
    current = path.read_text(encoding="utf-8") if path.exists() else ""

    if args.check:
        if current != rendered:
            print("✗ Plans.md is out of sync with tasks/index.json", file=sys.stderr)
            print("  Run: python3 scripts/sync_plans.py", file=sys.stderr)
            return 1
        print("✓ Plans.md in sync")
        return 0

    path.write_text(rendered, encoding="utf-8")
    print(f"✓ wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

