#!/usr/bin/env python3
"""Print a concise progress report from tasks/index.json."""

from __future__ import annotations

import argparse
from collections import Counter

from tasklib import STATUSES, add_common_args, ensure_valid_tasks, root_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Report JSON-backed task progress")
    add_common_args(parser)
    parser.add_argument("--task-id", help="show one task")
    args = parser.parse_args()

    tasks = ensure_valid_tasks(root_path(args.root))
    if args.task_id:
        tasks = [task for task in tasks if task.id == args.task_id]
        if not tasks:
            print(f"Task {args.task_id} not found")
            return 1

    counts = Counter(task.status for task in tasks)
    total = len(tasks)
    done = counts["done"]
    pct = int((done / total) * 100) if total else 0

    print(f"Progress: {done}/{total} done ({pct}%)")
    print("Status: " + ", ".join(f"{status}={counts[status]}" for status in sorted(STATUSES)))

    wip = [task for task in tasks if task.status == "wip"]
    todo = [task for task in tasks if task.status == "todo"]
    blocked = [task for task in tasks if task.status == "blocked"]

    print("WIP:")
    for task in wip:
        print(f"  {task.id} {task.title}")
    if not wip:
        print("  -")

    print("Next TODO:")
    for task in todo[:5]:
        print(f"  {task.id} {task.title}")
    if not todo:
        print("  -")

    print("Blocked:")
    for task in blocked:
        reason = f" — {task.blocked_reason}" if task.blocked_reason else ""
        print(f"  {task.id} {task.title}{reason}")
    if not blocked:
        print("  -")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

