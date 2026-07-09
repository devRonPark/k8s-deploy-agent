#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from planning_log import append_event


def task_dict(**overrides):
    data = {
        "id": "1.1",
        "title": "사용자가 로그인할 수 있게 하기",
        "dod": "사용자가 이메일과 비밀번호로 로그인할 수 있다",
        "acceptance": "pytest tests/test_login.py -q",
        "depends": [],
        "status": "todo",
        "gh": "-",
        "section": "Week 1",
    }
    data.update(overrides)
    return data


def write_repo(root: Path, tasks: list[dict]):
    (root / "tasks").mkdir(parents=True, exist_ok=True)
    (root / "tasks" / "index.json").write_text(
        json.dumps({"tasks": tasks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "Plans.md").write_text("stale\n", encoding="utf-8")


class PlanningLogTest(unittest.TestCase):
    def test_append_event_writes_human_fields_and_technical_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = append_event(
                root,
                step="작업 나누기 시작",
                result="시작",
                message="요청을 작업 단위로 나누기 시작했습니다.",
                next_action="잠시 기다리세요.",
                details_file=".harness/shared/planning/runs/plan/report.md",
                technical={"event": "decomposer.process.started", "run_id": "plan-test"},
            )
            event = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(event["step"], "작업 나누기 시작")
            self.assertEqual(event["result"], "시작")
            self.assertEqual(event["technical"]["run_id"], "plan-test")


class PlanningScriptsTest(unittest.TestCase):
    def run_script(self, *args: str, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / args[0]), "--root", str(root), *args[1:]],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_build_planning_context_creates_run_and_latest_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, [task_dict()])

            result = self.run_script(
                "build_planning_context.py",
                "--request",
                "로그인 기능을 만들고 싶다",
                "--run-id",
                "plan-test",
                root=root,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            context_path = root / ".harness/shared/planning/runs/plan-test/context.json"
            latest_path = root / ".harness/shared/planning/latest.json"
            self.assertTrue(context_path.exists())
            self.assertTrue(latest_path.exists())
            context = json.loads(context_path.read_text(encoding="utf-8"))
            self.assertEqual(context["run_id"], "plan-test")
            self.assertEqual(context["existing_tasks"][0]["id"], "1.1")

    def test_validate_proposal_rejects_duplicate_existing_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, [task_dict()])
            proposal = root / "proposal.json"
            proposal.write_text(json.dumps({"tasks": [task_dict()]}, ensure_ascii=False), encoding="utf-8")

            result = self.run_script("validate_task_proposal.py", "--proposal", str(proposal), root=root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicates an existing task id", result.stdout)

    def test_validate_proposal_reuses_acceptance_quality_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, [task_dict()])
            proposal = root / "proposal.json"
            proposal.write_text(
                json.dumps({"tasks": [task_dict(id="1.2", acceptance="pytest tests || echo skip")]}, ensure_ascii=False),
                encoding="utf-8",
            )

            result = self.run_script("validate_task_proposal.py", "--proposal", str(proposal), root=root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("mask failures", result.stdout)

    def test_run_task_decomposer_empty_command_logs_human_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, [task_dict()])
            context = root / "context.json"
            context.write_text("{}", encoding="utf-8")

            result = self.run_script(
                "run_task_decomposer.py",
                "--run-id",
                "plan-test",
                "--context",
                str(context),
                "--proposal",
                str(root / "proposal.json"),
                "--report",
                str(root / "report.md"),
                root=root,
            )

            self.assertNotEqual(result.returncode, 0)
            log_path = root / ".harness/events/planning.jsonl"
            event = json.loads(log_path.read_text(encoding="utf-8").strip())
            self.assertEqual(event["result"], "실패")
            self.assertIn("설정되어 있지", event["message"])
            self.assertEqual(event["technical"]["event"], "decomposer.process.missing_command")

    def test_apply_proposal_revalidates_current_tasks_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, [task_dict()])
            proposal = root / "proposal.json"
            proposal.write_text(
                json.dumps({"tasks": [task_dict(id="1.2", title="새 작업")]}, ensure_ascii=False),
                encoding="utf-8",
            )
            # Simulate another plan adding the same id after the proposal was produced.
            write_repo(root, [task_dict(), task_dict(id="1.2", title="이미 추가된 작업")])

            result = self.run_script("apply_task_proposal.py", "--proposal", str(proposal), root=root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicates an existing task id", result.stdout)

    def test_apply_proposal_appends_tasks_and_renders_plans(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, [task_dict(status="done")])
            proposal = root / "proposal.json"
            proposal.write_text(
                json.dumps({"tasks": [task_dict(id="1.2", title="비밀번호 재설정", depends=["1.1"])]}, ensure_ascii=False),
                encoding="utf-8",
            )

            result = self.run_script("apply_task_proposal.py", "--proposal", str(proposal), root=root)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            document = json.loads((root / "tasks/index.json").read_text(encoding="utf-8"))
            self.assertEqual([task["id"] for task in document["tasks"]], ["1.1", "1.2"])
            self.assertIn("비밀번호 재설정", (root / "Plans.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
