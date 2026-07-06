from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

# 소스 repo에는 생성 자산만 커밋 허용 — 사용자 코드 오염 방지
ALLOWED_COMMIT_TARGETS = ("Jenkinsfile", ".agent/")


class GitAdapter:
    """Commit generated assets into a source repository.

    dry_run=True (default): plan git commands without executing anything.
    dry_run=False: run git add/commit/push restricted to allowed files.
    """

    def __init__(self, repo_path: str | Path, *, dry_run: bool = True) -> None:
        self.repo_path = Path(repo_path)
        self.dry_run = dry_run

    def commit_and_push(
        self,
        files: Sequence[str],
        message: str,
        branch: str = "main",
    ) -> list[list[str]]:
        normalized = [str(path) for path in files]
        _validate_commit_targets(normalized)

        commands = [
            ["git", "add", "--", *normalized],
            ["git", "commit", "-m", message],
            ["git", "push", "origin", branch],
        ]
        if self.dry_run:
            return commands

        for command in commands:
            subprocess.run(command, cwd=self.repo_path, check=True, capture_output=True)
        return commands


def _validate_commit_targets(files: Sequence[str]) -> None:
    if not files:
        raise ValueError("No files to commit")

    disallowed = [path for path in files if not _is_allowed(path)]
    if disallowed:
        allowed = ", ".join(ALLOWED_COMMIT_TARGETS)
        raise ValueError(
            f"Files outside allowed commit scope ({allowed}): {', '.join(disallowed)}"
        )


def _is_allowed(path: str) -> bool:
    parts = PurePosixPath(path)
    if parts.is_absolute() or ".." in parts.parts:
        return False
    return path == "Jenkinsfile" or path.startswith(".agent/")
