#!/usr/bin/env python3
"""Print one task's fields from tasks/index.json without reading the whole file."""

from __future__ import annotations

import argparse

from tasklib import add_common_args, ensure_valid_tasks, root_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Show one task's fields from tasks/index.json")
    add_common_args(parser)
    parser.add_argument("task_id", help="task id, e.g. 8.4")
    args = parser.parse_args()

    tasks = {task.id: task for task in ensure_valid_tasks(root_path(args.root))}
    target = tasks.get(args.task_id)
    if target is None:
        print(f"Task {args.task_id} not found")
        return 1

    print(f"id: {target.id}")
    print(f"title: {target.title}")
    print(f"section: {target.section}")
    print(f"status: {target.status}")
    print(f"depends: {', '.join(target.depends) or '-'}")
    print(f"gh: {target.gh}")
    print(f"dod: {target.dod}")
    print(f"acceptance: {target.acceptance}")
    if target.blocked_reason:
        print(f"blocked_reason: {target.blocked_reason}")

    if target.depends:
        print("depends status:")
        for dep_id in target.depends:
            dep = tasks.get(dep_id)
            status = dep.status if dep else "MISSING"
            print(f"  {dep_id}: {status}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
