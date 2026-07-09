import subprocess
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import pytest

import k8s_deploy_agent.cli as cli
from k8s_deploy_agent.cli import main
from k8s_deploy_agent.config import DemoConfig
from k8s_deploy_agent.redaction import find_secret_leaks
from k8s_deploy_agent.source_repo import clone_source_repository
from k8s_deploy_agent.web import render_operator_console, run_console_dry_run, validate_console_payload


class InputNameParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.names: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "input":
            return
        attr_map = dict(attrs)
        name = attr_map.get("name")
        if name:
            self.names.append(name)


def write_sample_repo(root: Path) -> Path:
    repo = root / "sample-repo"
    backend = repo / "backend"
    backend.mkdir(parents=True)
    (backend / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (backend / "Dockerfile").write_text("FROM python:3.12\nEXPOSE 8000\n", encoding="utf-8")
    backend_app = backend / "app"
    backend_app.mkdir()
    (backend_app / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

    frontend = repo / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text(
        '{"scripts":{"build":"vite build","start":"vite --host 0.0.0.0 --port 3000"},"dependencies":{"vite":"latest"}}\n',
        encoding="utf-8",
    )
    (frontend / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (frontend / "Dockerfile").write_text("FROM node:22\nEXPOSE 3000\n", encoding="utf-8")
    return repo


def write_config(root: Path, *, source_repo_url: str = "https://gitea.example.local/team/source.git") -> Path:
    config = root / "demo-inputs.yaml"
    config.write_text(
        "\n".join(
            [
                f'source_repo_url: "{source_repo_url}"',
                "source_branch: main",
                "source_credential_id: gitea-source-credential",
                'gitops_repo_url: "https://gitea.example.local/team/gitops.git"',
                "gitops_branch: main",
                "gitops_path: .",
                "gitops_credential_id: gitea-gitops-credential",
                "app_name: fastapi-demo",
                "environment: dev",
                "registry_url: registry.example.local",
                "registry_project: demo",
                "registry_credential_id: suse-registry-credential",
                "registry_ca_cert_credential_id: suse-registry-ca-cert",
            ]
        ),
        encoding="utf-8",
    )
    return config


def init_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.local"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True)


def console_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "app_name": "fastapi-demo",
        "environment": "dev",
        "target_namespace": "fastapi-demo-dev",
        "source_repo_url": "https://gitea.example.local/team/source.git",
        "source_branch": "main",
        "source_credential_id": "gitea-source-credential",
        "source_access_token_env": "K8S_DEPLOY_AGENT_SOURCE_TOKEN",
        "gitops_repo_url": "https://gitea.example.local/team/gitops.git",
        "gitops_branch": "main",
        "gitops_path": "apps/fastapi-demo",
        "gitops_credential_id": "gitea-gitops-credential",
        "registry_url": "registry.example.local",
        "registry_project": "demo",
        "registry_credential_id": "suse-registry-credential",
        "registry_ca_cert_credential_id": "suse-registry-ca-cert",
    }
    payload.update(overrides)
    return payload


def test_dry_run_generates_assets_for_root_level_repo(tmp_path):
    repo = tmp_path / "root-fastapi"
    repo.mkdir()
    (repo / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (repo / "Dockerfile").write_text("FROM python:3.12\nEXPOSE 8000\n", encoding="utf-8")
    app = repo / "app"
    app.mkdir()
    (app / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    config = write_config(tmp_path)
    output = tmp_path / "out"

    exit_code = main(
        [
            "dry-run",
            "--config",
            str(config),
            "--repo",
            str(repo),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    assert (output / "gitops/apps/root-fastapi/deployment.yaml").is_file()
    assert (output / "dockerfile-proposals/root-fastapi/Dockerfile").is_file()

    jenkinsfile = (output / "Jenkinsfile").read_text(encoding="utf-8")
    assert "--context=${WORKSPACE}/." in jenkinsfile
    assert "--dockerfile=${WORKSPACE}/Dockerfile" in jenkinsfile

    report = (output / ".agent/reports/repository-analysis.md").read_text(encoding="utf-8")
    assert "| root-fastapi | python | . | Dockerfile |" in report
    assert "| root-fastapi | python | pip | uvicorn app.main:app --host 0.0.0.0 | 8000 | confirmed | - |" in report


def test_dry_run_generates_demo_assets(tmp_path):
    repo = write_sample_repo(tmp_path)
    config = write_config(tmp_path)
    output = tmp_path / "out"

    exit_code = main(
        [
            "dry-run",
            "--config",
            str(config),
            "--repo",
            str(repo),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    assert (output / "index.html").is_file()
    assert (output / "Jenkinsfile").is_file()
    assert (output / ".agent/reports/repository-analysis.md").is_file()
    assert (output / "gitops/fleet.yaml").is_file()
    assert (output / "gitops/apps/backend/deployment.yaml").is_file()
    assert (output / "gitops/apps/frontend/deployment.yaml").is_file()
    assert (output / "dockerfile-proposals/backend/Dockerfile").is_file()
    assert (output / "dockerfile-proposals/backend/.dockerignore").is_file()
    assert (output / "dockerfile-proposals/frontend/Dockerfile").is_file()
    assert (output / "dockerfile-proposals/frontend/.dockerignore").is_file()
    assert (output / "dockerfile-proposals/VALIDATION.md").is_file()

    dashboard = (output / "index.html").read_text(encoding="utf-8")
    assert "fastapi-demo 배포 미리보기" in dashboard
    assert "서비스 준비 상태" in dashboard
    assert "생성된 산출물" in dashboard

    jenkinsfile = (output / "Jenkinsfile").read_text(encoding="utf-8")
    assert "podTemplate(" in jenkinsfile
    assert "Build and Push Images" in jenkinsfile
    assert "Update GitOps Repository" in jenkinsfile

    report = (output / ".agent/reports/repository-analysis.md").read_text(encoding="utf-8")
    assert "## Build Profiles" in report
    assert "| backend | python | pip |" in report
    assert "### Build Profile Evidence" in report

    dockerfile = (output / "dockerfile-proposals/backend/Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:3.12-slim AS runtime" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert 'CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000"]' in dockerfile

    node_dockerfile = (output / "dockerfile-proposals/frontend/Dockerfile").read_text(encoding="utf-8")
    assert "FROM node:22 AS build" in node_dockerfile
    assert "RUN pnpm run build" in node_dockerfile
    validation = (output / "dockerfile-proposals/VALIDATION.md").read_text(encoding="utf-8")
    assert "| Secret redaction | pass |" in validation
    assert "| Review-only output | pass |" in validation
    assert "| Confidence gate | pass |" in validation


def test_dry_run_clones_source_repo_from_config_when_repo_is_omitted(tmp_path):
    repo = write_sample_repo(tmp_path)
    init_git_repo(repo)
    config = write_config(tmp_path, source_repo_url=repo.as_posix())
    output = tmp_path / "out"

    exit_code = main(
        [
            "dry-run",
            "--config",
            str(config),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    assert (output / "gitops/apps/backend/deployment.yaml").is_file()
    assert (output / "gitops/apps/frontend/deployment.yaml").is_file()

    report = (output / ".agent/reports/repository-analysis.md").read_text(encoding="utf-8")
    assert "| backend | python | backend | backend/Dockerfile |" in report
    assert "| frontend | node | frontend | frontend/Dockerfile |" in report


def minimal_demo_config(**overrides: object) -> DemoConfig:
    fields: dict[str, object] = {
        "source_repo_url": "https://gitea.example.local/team/source.git",
        "source_branch": "main",
        "source_credential_id": "public-source",
        "gitops_repo_url": "https://gitops.example.local/review-only.git",
        "gitops_branch": "main",
        "gitops_path": ".",
        "gitops_credential_id": "review-only-gitops-credential",
        "app_name": "demo",
        "environment": "dev",
    }
    fields.update(overrides)
    return DemoConfig(**fields)


def test_clone_source_repository_anonymous_failure_includes_credential_hint(tmp_path):
    config = minimal_demo_config(source_repo_url=(tmp_path / "missing-repo").as_posix())
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    with pytest.raises(ValueError) as excinfo:
        clone_source_repository(config, work_dir)

    assert "private repository면 source credential ID를 입력하세요" in str(excinfo.value)


def test_clone_source_repository_authenticated_failure_omits_credential_hint(tmp_path, monkeypatch):
    monkeypatch.setenv("K8S_DEPLOY_AGENT_TEST_TOKEN", "x" * 40)
    config = minimal_demo_config(
        source_repo_url=(tmp_path / "missing-repo").as_posix(),
        source_access_token_env="K8S_DEPLOY_AGENT_TEST_TOKEN",
    )
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    with pytest.raises(ValueError) as excinfo:
        clone_source_repository(config, work_dir)

    assert "private repository면 source credential ID를 입력하세요" not in str(excinfo.value)


def test_redaction_detects_token_like_values_even_in_credential_id_fields():
    leaks = find_secret_leaks(
        {
            "Jenkinsfile": "usernamePassword(credentialsId: 'github_pat_abcdefghijklmnopqrstuvwxyz1234567890')",
        }
    )

    assert leaks


def test_web_command_dispatches_local_console(monkeypatch):
    called = {}

    def fake_run_web_server(host: str, port: int) -> None:
        called["host"] = host
        called["port"] = port

    monkeypatch.setattr(cli, "run_web_server", fake_run_web_server)

    exit_code = main(["web", "--host", "127.0.0.1", "--port", "9090"])

    assert exit_code == 0
    assert called == {"host": "127.0.0.1", "port": 9090}


def test_operator_console_shell_is_offline_first_and_secret_safe():
    html = render_operator_console()

    assert "k8s-deploy-agent operator console" in html
    assert 'method="post"' in html
    assert 'action="/validate"' in html
    assert 'formaction="/dry-run"' in html
    assert 'name="source_input_mode" value="clone" checked' in html
    assert 'name="source_input_mode" value="local"' in html
    assert 'name="local_source_repo_path"' in html
    assert 'class="clone-source-fields"' in html
    assert 'class="local-source-fields"' in html
    assert 'form:has(input[name="source_input_mode"][value="clone"]:checked) .local-source-fields' in html
    assert 'form:has(input[name="source_input_mode"][value="local"]:checked) .clone-source-fields' in html
    assert "Source credential ID (Private repo only)" in html
    assert "local source repository path (absolute path)" in html
    assert "입력 검증" in html
    assert "dry-run 실행" in html
    assert "credential ID만 입력" in html
    assert "1. 입력" in html
    assert "2. 검증" in html
    assert "3. dry-run" in html
    assert "4. 분석 / 산출물 리뷰" in html
    assert "5. 검증 checklist" in html
    assert "작업 대상" in html
    assert "GitOps target" in html
    assert "Private registry" in html
    assert "source repository URL clone" in html
    assert "FastAPI public sample" in html
    assert 'formaction="/sample"' in html
    assert "https://github.com/fastapi/full-stack-fastapi-template.git" in html
    assert "서버 local path 분석" in html
    assert "향후 확장" in html
    assert "assert_no_secret_values" in html
    assert "<script" not in html
    assert 'href="http' not in html
    assert 'src="http' not in html
    assert 'type="password"' not in html


def test_operator_console_form_has_no_duplicate_input_names_except_source_mode_radio_group():
    parser = InputNameParser()
    parser.feed(render_operator_console())

    duplicate_names = {
        name: count
        for name, count in Counter(parser.names).items()
        if count > 1
    }

    assert duplicate_names == {"source_input_mode": 2}


def test_console_payload_validation_accepts_demo_config_compatible_input():
    result = validate_console_payload(console_payload())

    assert result.ok
    assert result.config is not None
    assert result.config.namespace == "fastapi-demo-dev"
    assert result.messages == ()


def test_console_payload_validation_clone_mode_requires_source_clone_fields():
    result = validate_console_payload(
        console_payload(
            source_input_mode="clone",
            source_repo_url="",
            source_branch="",
            source_credential_id="",
        )
    )

    assert not result.ok
    assert any(
        "Missing required config fields: source_repo_url, source_branch, source_credential_id" in message
        for message in result.messages
    )


def test_console_payload_validation_public_github_clone_requires_only_url_and_branch():
    result = validate_console_payload(
        console_payload(
            source_input_mode="clone",
            source_repo_url="https://github.com/fastapi/full-stack-fastapi-template.git",
            source_branch="main",
            source_credential_id="",
            source_access_token_env="",
        )
    )

    assert result.ok
    assert result.config is not None
    assert result.config.source_repo_url == "https://github.com/fastapi/full-stack-fastapi-template.git"
    assert result.config.source_branch == "main"
    assert result.config.source_credential_id == "public-source"
    assert result.config.source_access_token_env is None


def test_console_payload_validation_arbitrary_public_clone_allows_empty_credential():
    result = validate_console_payload(
        console_payload(
            source_input_mode="clone",
            source_repo_url="https://github.com/octocat/Hello-World.git",
            source_branch="master",
            source_credential_id="",
            source_access_token_env="",
        )
    )

    assert result.ok
    assert result.config is not None
    assert result.config.source_repo_url == "https://github.com/octocat/Hello-World.git"
    assert result.config.source_branch == "master"
    assert result.config.source_credential_id == "public-source"
    assert result.config.source_access_token_env is None


def test_console_payload_validation_allows_first_test_without_gitops_target():
    result = validate_console_payload(
        console_payload(
            gitops_repo_url="",
            gitops_branch="",
            gitops_path="",
            gitops_credential_id="",
            registry_url="",
            registry_project="",
            registry_credential_id="",
            registry_ca_cert_credential_id="",
        )
    )

    assert result.ok
    assert result.config is not None
    assert result.messages == ()
    assert result.config.gitops_repo_url == "https://gitops.example.local/review-only.git"
    assert result.config.gitops_branch == "main"
    assert result.config.gitops_path == "apps/fastapi-demo"
    assert result.config.gitops_credential_id == "review-only-gitops-credential"


def test_console_payload_validation_local_mode_uses_path_without_clone_fields(tmp_path):
    repo = write_sample_repo(tmp_path)

    result = validate_console_payload(
        console_payload(
            source_input_mode="local",
            local_source_repo_path=repo.as_posix(),
            source_repo_url="",
            source_branch="",
            source_credential_id="",
        )
    )

    assert result.ok
    assert result.config is not None
    assert result.config.source_repo_url == repo.resolve().as_posix()
    assert result.config.source_branch == "local"
    assert result.config.source_credential_id == "local-source"


def test_console_payload_validation_local_mode_blocks_invalid_repo_paths(tmp_path):
    file_path = tmp_path / "not-a-directory.txt"
    file_path.write_text("not a repo\n", encoding="utf-8")

    empty_path = validate_console_payload(console_payload(source_input_mode="local", local_source_repo_path=""))
    missing_path = validate_console_payload(
        console_payload(source_input_mode="local", local_source_repo_path=(tmp_path / "missing").as_posix())
    )
    regular_file = validate_console_payload(
        console_payload(source_input_mode="local", local_source_repo_path=file_path.as_posix())
    )

    assert not empty_path.ok
    assert any("local_source_repo_path가 필요합니다" in message for message in empty_path.messages)
    assert not missing_path.ok
    assert any("존재하지 않습니다" in message for message in missing_path.messages)
    assert not regular_file.ok
    assert any("directory가 아닙니다" in message for message in regular_file.messages)


def test_console_payload_validation_rejects_secret_like_values():
    result = validate_console_payload(
        {
            "app_name": "fastapi-demo",
            "environment": "dev",
            "source_repo_url": "https://gitea.example.local/team/source.git",
            "source_branch": "main",
            "source_credential_id": "github_pat_abcdefghijklmnopqrstuvwxyz1234567890",
            "gitops_repo_url": "https://gitea.example.local/team/gitops.git",
            "gitops_branch": "main",
            "gitops_path": "apps/fastapi-demo",
            "gitops_credential_id": "gitea-gitops-credential",
        }
    )

    assert not result.ok
    assert result.config is not None
    assert any("Secret value detected" in message for message in result.messages)


def test_console_payload_validation_local_mode_rejects_secret_like_values(tmp_path):
    repo = write_sample_repo(tmp_path)

    result = validate_console_payload(
        console_payload(
            source_input_mode="local",
            local_source_repo_path=repo.as_posix(),
            source_repo_url="",
            source_branch="",
            source_credential_id="",
            registry_credential_id="github_pat_abcdefghijklmnopqrstuvwxyz1234567890",
        )
    )

    assert not result.ok
    assert result.config is not None
    assert any("Secret value detected" in message for message in result.messages)


def test_console_dry_run_execution_reuses_cli_pipeline(tmp_path):
    repo = write_sample_repo(tmp_path)
    init_git_repo(repo)

    result = run_console_dry_run(console_payload(source_repo_url=repo.as_posix()))

    assert result.ok
    assert result.output_dir is not None
    assert result.validation is not None and result.validation.ok
    output_dir = Path(result.output_dir)
    assert (output_dir / "Jenkinsfile").is_file()
    assert (output_dir / "index.html").is_file()
    assert (output_dir / "gitops/apps/backend/deployment.yaml").is_file()
    assert any(path.endswith("Jenkinsfile") for path in result.generated_paths)


def test_console_dry_run_preview_and_checklist_render_generated_files(tmp_path):
    repo = write_sample_repo(tmp_path)
    init_git_repo(repo)

    result = run_console_dry_run(console_payload(source_repo_url=repo.as_posix()))

    html = render_operator_console(validation=result.validation, dry_run=result)

    assert "4. 분석 / 산출물 리뷰" in html
    assert "Repository analysis" in html
    assert "CI pipeline" in html
    assert "GitOps base" in html
    assert "Service manifests" in html
    assert ".agent/reports/repository-analysis.md" in html
    assert "dockerfile-proposals/VALIDATION.md" in html
    assert "Jenkinsfile" in html
    assert "5. 검증 checklist" in html
    assert "Dockerfile proposals" in html
    assert "Namespace 정합성" in html
    assert "Secret redaction" in html
    assert "생성 assets" in html


def test_console_dry_run_local_mode_generates_assets_from_valid_repo_path(tmp_path):
    repo = write_sample_repo(tmp_path)

    result = run_console_dry_run(
        console_payload(
            source_input_mode="local",
            local_source_repo_path=repo.as_posix(),
        )
    )

    assert result.ok
    assert result.output_dir is not None
    output_dir = Path(result.output_dir)
    assert (output_dir / "Jenkinsfile").is_file()
    assert (output_dir / "gitops/apps/backend/deployment.yaml").is_file()
    assert (output_dir / "gitops/apps/frontend/deployment.yaml").is_file()


def test_console_dry_run_local_mode_allows_first_test_without_gitops_target(tmp_path):
    repo = write_sample_repo(tmp_path)

    result = run_console_dry_run(
        console_payload(
            source_input_mode="local",
            local_source_repo_path=repo.as_posix(),
            source_repo_url="",
            source_branch="",
            source_credential_id="",
            source_access_token_env="",
            gitops_repo_url="",
            gitops_branch="",
            gitops_path="",
            gitops_credential_id="",
            registry_url="",
            registry_project="",
            registry_credential_id="",
            registry_ca_cert_credential_id="",
        )
    )

    assert result.ok
    assert result.config is not None
    assert result.config.gitops_path == "apps/fastapi-demo"
    assert result.output_dir is not None
    output_dir = Path(result.output_dir)
    assert (output_dir / "Jenkinsfile").is_file()
    assert (output_dir / "gitops/fleet.yaml").is_file()
    assert (output_dir / "gitops/apps/backend/deployment.yaml").is_file()


def test_console_dry_run_local_mode_blocks_invalid_repo_paths(tmp_path):
    file_path = tmp_path / "not-a-directory.txt"
    file_path.write_text("not a repo\n", encoding="utf-8")

    empty_path = run_console_dry_run(console_payload(source_input_mode="local", local_source_repo_path=""))
    missing_path = run_console_dry_run(
        console_payload(source_input_mode="local", local_source_repo_path=(tmp_path / "missing").as_posix())
    )
    regular_file = run_console_dry_run(
        console_payload(source_input_mode="local", local_source_repo_path=file_path.as_posix())
    )

    assert not empty_path.ok
    assert any("local_source_repo_path가 필요합니다" in message for message in empty_path.messages)
    assert not missing_path.ok
    assert any("존재하지 않습니다" in message for message in missing_path.messages)
    assert not regular_file.ok
    assert any("directory가 아닙니다" in message for message in regular_file.messages)


def test_console_dry_run_blocks_invalid_source_input_mode():
    result = run_console_dry_run(console_payload(source_input_mode="archive"))

    assert not result.ok
    assert any("source_input_mode는 clone 또는 local이어야 합니다" in message for message in result.messages)


def test_console_clone_mode_ignores_local_source_repo_path(tmp_path):
    repo = write_sample_repo(tmp_path)
    init_git_repo(repo)
    not_a_directory = tmp_path / "ignored-local-path.txt"
    not_a_directory.write_text("ignored\n", encoding="utf-8")

    result = run_console_dry_run(
        console_payload(
            source_input_mode="clone",
            source_repo_url=repo.as_posix(),
            local_source_repo_path=not_a_directory.as_posix(),
        )
    )

    assert result.ok
    assert result.output_dir is not None
    assert (Path(result.output_dir) / "gitops/apps/backend/deployment.yaml").is_file()


def test_operator_console_retains_submitted_source_mode_and_local_path(tmp_path):
    repo = write_sample_repo(tmp_path)
    payload = console_payload(source_input_mode="local", local_source_repo_path=repo.as_posix())
    validation = validate_console_payload(payload)

    html = render_operator_console(validation=validation, form_values=payload)

    assert 'name="source_input_mode" value="local" checked' in html
    assert f'name="local_source_repo_path" value="{repo.as_posix()}"' in html


def test_console_payload_validation_local_mode_ignores_hidden_clone_fields(tmp_path):
    repo = write_sample_repo(tmp_path)

    result = validate_console_payload(
        console_payload(
            source_input_mode="local",
            local_source_repo_path=repo.as_posix(),
            source_repo_url="",
            source_branch="",
            source_credential_id="github_pat_abcdefghijklmnopqrstuvwxyz1234567890",
            source_access_token_env="not-an-env-var",
        )
    )

    assert result.ok
    assert result.config is not None
    assert result.config.source_repo_url == repo.resolve().as_posix()
    assert result.config.source_branch == "local"
    assert result.config.source_credential_id == "local-source"
