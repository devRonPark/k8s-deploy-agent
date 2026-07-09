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

from tasklib import Task, render_plans, validate_tasks


def task(**overrides):
    data = {
        "id": "1.1",
        "title": "Login endpoint",
        "dod": "200 response",
        "acceptance": "pytest tests/test_auth.py -k login",
        "depends": [],
        "status": "todo",
        "gh": "-",
        "section": "Week 1",
    }
    data.update(overrides)
    return Task.from_dict(data, 0)


class TaskValidationTest(unittest.TestCase):
    def test_valid_tasks_pass(self):
        tasks = [task(status="done"), task(id="1.2", depends=["1.1"], status="wip")]
        self.assertEqual(validate_tasks(tasks), [])

    def test_duplicate_task_id_fails(self):
        errors = validate_tasks([task(), task()])
        self.assertTrue(any("duplicate" in error for error in errors))

    def test_missing_depends_fails(self):
        errors = validate_tasks([task(depends=["9.9"])])
        self.assertTrue(any("missing task 9.9" in error for error in errors))

    def test_wip_depends_must_be_done(self):
        tasks = [task(id="1.1", status="todo"), task(id="1.2", depends=["1.1"], status="wip")]
        errors = validate_tasks(tasks)
        self.assertTrue(any("but it is todo" in error for error in errors))

    def test_wip_acceptance_required(self):
        errors = validate_tasks([task(status="wip", acceptance="")])
        self.assertTrue(any("requires acceptance" in error for error in errors))

    def test_acceptance_must_not_mask_failures(self):
        errors = validate_tasks([task(acceptance="pytest tests || echo skip")])
        self.assertTrue(any("mask failures" in error for error in errors))

    def test_acceptance_must_not_be_noop(self):
        errors = validate_tasks([task(acceptance="true")])
        self.assertTrue(any("not a no-op" in error for error in errors))

    def test_acceptance_must_stay_inside_repo(self):
        errors = validate_tasks([task(acceptance="test -f ../other-repo/Plans.md")])
        self.assertTrue(any("outside the repo" in error for error in errors))

    def test_dash_acceptance_is_allowed_for_non_wip_tasks(self):
        self.assertEqual(validate_tasks([task(acceptance="-")]), [])


class SyncPlansTest(unittest.TestCase):
    def test_render_is_deterministic(self):
        tasks = [
            task(id="1.1", status="done", acceptance="grep -q 'a|b' README.md"),
            task(id="1.2", title="Next", depends=["1.1"], status="todo"),
        ]
        first = render_plans(ROOT, tasks)
        second = render_plans(ROOT, tasks)
        self.assertEqual(first, second)
        self.assertIn(r"grep -q 'a\|b' README.md", first)
        self.assertIn("| 1.2 | Next |", first)

    def test_sync_check_detects_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tasks").mkdir()
            (root / "scripts").symlink_to(ROOT / "scripts", target_is_directory=True)
            document = {"tasks": [task(status="todo").to_dict()]}
            (root / "tasks" / "index.json").write_text(json.dumps(document), encoding="utf-8")
            (root / "Plans.md").write_text("stale\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "sync_plans.py"), "--root", str(root), "--check"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
