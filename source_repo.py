from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from k8s_deploy_agent.config import DemoConfig


def clone_source_repository(config: DemoConfig, work_dir: str | Path) -> Path:
    destination = Path(work_dir) / "source"
    command = [
        "git",
        "clone",
        "--depth",
        "1",
        "--branch",
        config.source_branch,
        config.source_repo_url,
        str(destination),
    ]
    env = os.environ.copy()
    source_token = _source_access_token(config)
    askpass = _write_askpass(Path(work_dir), source_token)
    if askpass is not None:
        env.update(
            {
                "GIT_ASKPASS": str(askpass),
                "GIT_TERMINAL_PROMPT": "0",
                "K8S_DEPLOY_AGENT_GIT_USERNAME": "x-access-token",
                "K8S_DEPLOY_AGENT_GIT_PASSWORD": source_token,
            }
        )

    result = subprocess.run(command, check=False, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        detail = _sanitize_error(result.stderr or result.stdout)
        message = f"Failed to clone source repository: {detail}"
        if askpass is None:
            message += " private repository면 source credential ID를 입력하세요."
        raise ValueError(message)
    return destination


def _source_access_token(config: DemoConfig) -> str:
    if config.source_access_token_env:
        return os.environ.get(config.source_access_token_env, "")
    if _is_http_token_like(config.source_credential_id):
        return config.source_credential_id
    return ""


def _write_askpass(work_dir: Path, credential: str) -> Path | None:
    if not credential or not _is_http_token_like(credential):
        return None

    askpass = work_dir / "git-askpass.sh"
    askpass.write_text(
        "\n".join(
            [
                "#!/bin/sh",
                "case \"$1\" in",
                "  *Username*) printf '%s\\n' \"$K8S_DEPLOY_AGENT_GIT_USERNAME\" ;;",
                "  *) printf '%s\\n' \"$K8S_DEPLOY_AGENT_GIT_PASSWORD\" ;;",
                "esac",
                "",
            ]
        ),
        encoding="utf-8",
    )
    askpass.chmod(askpass.stat().st_mode | stat.S_IXUSR)
    return askpass


def _is_http_token_like(value: str) -> bool:
    return (
        value.startswith(("github_pat_", "ghp_", "gho_", "glpat-"))
        or len(value) >= 32
    )


def _sanitize_error(message: str) -> str:
    cleaned = " ".join(message.split())
    return cleaned or "git clone exited with a non-zero status"
