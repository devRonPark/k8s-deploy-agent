#!/usr/bin/env python3
"""Append human-readable planning events as JSONL."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from tasklib import add_common_args, root_path


DEFAULT_LOG_PATH = ".harness/events/planning.jsonl"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_technical(values: list[str]) -> dict[str, Any]:
    technical: dict[str, Any] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"--technical must use key=value form: {value}")
        key, raw = value.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("--technical key must not be empty")
        technical[key] = raw
    return technical


def append_event(
    root: Path,
    *,
    step: str,
    result: str,
    message: str,
    next_action: str = "",
    details_file: str = "",
    technical: dict[str, Any] | None = None,
    log_path: str = DEFAULT_LOG_PATH,
) -> Path:
    path = root / log_path
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "time": now_iso(),
        "step": step,
        "result": result,
        "message": message,
        "next_action": next_action,
        "details_file": details_file,
        "technical": technical or {},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Append one planning event to JSONL")
    add_common_args(parser)
    parser.add_argument("--log-path", default=DEFAULT_LOG_PATH, help=f"default: {DEFAULT_LOG_PATH}")
    parser.add_argument("--step", required=True, help="human-readable step name")
    parser.add_argument("--result", required=True, help="시작, 성공, 실패, 반영됨")
    parser.add_argument("--message", required=True, help="human-readable event message")
    parser.add_argument("--next-action", default="", help="what the user should do next")
    parser.add_argument("--details-file", default="", help="path to a human-readable details file")
    parser.add_argument(
        "--technical",
        action="append",
        default=[],
        help="technical key=value metadata; may be repeated",
    )
    args = parser.parse_args()

    try:
        technical = parse_technical(args.technical)
        path = append_event(
            root_path(args.root),
            step=args.step,
            result=args.result,
            message=args.message,
            next_action=args.next_action,
            details_file=args.details_file,
            technical=technical,
            log_path=args.log_path,
        )
    except Exception as exc:
        print(f"✗ {exc}")
        return 1

    print(f"✓ wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
