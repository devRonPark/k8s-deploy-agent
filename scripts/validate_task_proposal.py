#!/usr/bin/env python3
"""Validate a proposed task JSON file before applying it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tasklib import Task, add_common_args, load_tasks, root_path, validate_tasks


def load_proposed_tasks(path: Path) -> list[Task]:
    if not path.exists():
        raise ValueError(f"{path} not found")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON at line {exc.lineno}: {exc.msg}") from exc

    items: Any
    if isinstance(raw, dict):
        items = raw.get("tasks")
    else:
        items = raw
    if not isinstance(items, list):
        raise ValueError("proposal must be a task array or an object with a tasks array")

    tasks: list[Task] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"proposal task[{index}] must be an object")
        tasks.append(Task.from_dict(item, index))
    return tasks


def validate_proposal(existing: list[Task], proposed: list[Task]) -> list[str]:
    errors: list[str] = []
    existing_ids = {task.id for task in existing}
    for task in proposed:
        if task.id in existing_ids:
            errors.append(f"{task.id}: proposal duplicates an existing task id")
        if task.status != "todo":
            errors.append(f"{task.id}: proposed task status must be todo")
        if task.gh != "-":
            errors.append(f"{task.id}: proposed task gh must be '-'")

    errors.extend(validate_tasks(existing + proposed))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate task proposal JSON")
    add_common_args(parser)
    parser.add_argument("--proposal", required=True, help="path to proposed-tasks.json")
    args = parser.parse_args()

    root = root_path(args.root)
    try:
        existing = load_tasks(root)
        proposed = load_proposed_tasks((root / args.proposal).resolve() if not Path(args.proposal).is_absolute() else Path(args.proposal))
        errors = validate_proposal(existing, proposed)
    except Exception as exc:
        print(f"✗ {exc}")
        return 1

    if errors:
        for error in errors:
            print(f"✗ {error}")
        return 1

    print(f"✓ proposal valid ({len(proposed)} tasks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
