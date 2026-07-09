#!/usr/bin/env python3
"""Run the configured task decomposer command for one planning context."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path

from planning_log import append_event
from tasklib import add_common_args, root_path


def format_command(command: str, context: Path, proposal: Path, report: Path) -> list[str]:
    rendered = command.format(context=str(context), proposal=str(proposal), report=str(report))
    return shlex.split(rendered)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run external task decomposer command")
    add_common_args(parser)
    parser.add_argument("--command", default="", help="external command; supports {context}, {proposal}, {report}")
    parser.add_argument("--context", required=True, help="path to context.json")
    parser.add_argument("--proposal", required=True, help="path expected for proposed-tasks.json")
    parser.add_argument("--report", required=True, help="path expected for decomposition-report.md")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    root = root_path(args.root)
    context = Path(args.context)
    proposal = Path(args.proposal)
    report = Path(args.report)
    if not context.is_absolute():
        context = root / context
    if not proposal.is_absolute():
        proposal = root / proposal
    if not report.is_absolute():
        report = root / report

    if not args.command.strip():
        append_event(
            root,
            step="작업 나누기 시작",
            result="실패",
            message="독립 task-decomposer 명령이 설정되어 있지 않아 자동으로 작업을 나누지 못했습니다.",
            next_action="harness.toml의 decomposer_command를 설정하거나 inline fallback으로 같은 proposal 파일을 작성하세요.",
            details_file=str(report.relative_to(root) if report.is_relative_to(root) else report),
            technical={"event": "decomposer.process.missing_command", "run_id": args.run_id},
        )
        print("✗ decomposer command is empty")
        return 1

    try:
        command = format_command(args.command, context, proposal, report)
        append_event(
            root,
            step="작업 나누기 시작",
            result="시작",
            message="독립 task-decomposer 명령을 실행합니다.",
            details_file=str(report.relative_to(root) if report.is_relative_to(root) else report),
            technical={"event": "decomposer.process.started", "run_id": args.run_id, "command": command},
        )
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            append_event(
                root,
                step="작업 나누기",
                result="실패",
                message="독립 task-decomposer 명령이 실패했습니다.",
                next_action="명령 출력과 decomposition report를 확인한 뒤 다시 실행하거나 inline fallback을 사용하세요.",
                details_file=str(report.relative_to(root) if report.is_relative_to(root) else report),
                technical={
                    "event": "decomposer.process.failed",
                    "run_id": args.run_id,
                    "command_exit_code": result.returncode,
                    "stderr": result.stderr.strip(),
                },
            )
            print(result.stdout, end="")
            print(result.stderr, end="")
            return result.returncode

        missing = [str(path) for path in (proposal, report) if not path.exists()]
        if missing:
            append_event(
                root,
                step="작업 나누기",
                result="실패",
                message="독립 task-decomposer 명령은 끝났지만 필요한 결과 파일이 없습니다.",
                next_action="명령이 proposed-tasks.json과 decomposition-report.md를 모두 생성하는지 확인하세요.",
                details_file=str(report.relative_to(root) if report.is_relative_to(root) else report),
                technical={"event": "decomposer.process.missing_outputs", "run_id": args.run_id, "files": missing},
            )
            print(f"✗ missing decomposer outputs: {', '.join(missing)}")
            return 1

        append_event(
            root,
            step="작업 나누기 완료",
            result="성공",
            message="독립 task-decomposer가 작업 제안과 설명 보고서를 만들었습니다.",
            next_action="성공 기준 검사를 실행하세요.",
            details_file=str(report.relative_to(root) if report.is_relative_to(root) else report),
            technical={
                "event": "decomposer.proposal.created",
                "run_id": args.run_id,
                "files": [str(proposal), str(report)],
            },
        )
    except Exception as exc:
        append_event(
            root,
            step="작업 나누기",
            result="실패",
            message="독립 task-decomposer 실행 중 예상하지 못한 오류가 났습니다.",
            next_action="오류 내용을 확인한 뒤 명령 설정을 고치거나 inline fallback을 사용하세요.",
            details_file=str(report),
            technical={"event": "decomposer.process.error", "run_id": args.run_id, "error": str(exc)},
        )
        print(f"✗ {exc}")
        return 1

    print(f"✓ wrote {proposal}")
    print(f"✓ wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
