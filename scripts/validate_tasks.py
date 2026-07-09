#!/usr/bin/env python3
"""Validate tasks/index.json."""

from __future__ import annotations

import argparse
import sys

from tasklib import add_common_args, root_path, validate_tasks, load_tasks


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate JSON-backed task state")
    add_common_args(parser)
    parser.add_argument("--task-id", help="validate only this task and global references")
    args = parser.parse_args()

    root = root_path(args.root)
    try:
        tasks = load_tasks(root)
        if args.task_id:
            if not any(task.id == args.task_id for task in tasks):
                print(f"Task {args.task_id} not found", file=sys.stderr)
                return 1
        errors = validate_tasks(tasks)
    except Exception as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1

    if errors:
        for error in errors:
            print(f"✗ {error}", file=sys.stderr)
        return 1

    print(f"✓ tasks/index.json valid ({len(tasks)} tasks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

