import subprocess
from pathlib import Path

import k8s_deploy_agent.cli as cli
from k8s_deploy_agent.cli import main
from k8s_deploy_agent.redaction import find_secret_leaks
from k8s_deploy_agent.web import render_operator_console, run_console_dry_run, validate_console_payload


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
    assert "Validate payload" in html
    assert "Run dry-run" in html
    assert "credential ID only" in html
    assert "assert_no_secret_values" in html
    assert "<script" not in html
    assert 'href="http' not in html
    assert 'src="http' not in html
    assert 'type="password"' not in html


def test_console_payload_validation_accepts_demo_config_compatible_input():
    result = validate_console_payload(
        {
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
    )

    assert result.ok
    assert result.config is not None
    assert result.config.namespace == "fastapi-demo-dev"
    assert result.messages == ()


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


def test_console_dry_run_execution_reuses_cli_pipeline(tmp_path):
    repo = write_sample_repo(tmp_path)
    init_git_repo(repo)

    result = run_console_dry_run(
        {
            "app_name": "fastapi-demo",
            "environment": "dev",
            "target_namespace": "fastapi-demo-dev",
            "source_repo_url": repo.as_posix(),
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
    )

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

    result = run_console_dry_run(
        {
            "app_name": "fastapi-demo",
            "environment": "dev",
            "target_namespace": "fastapi-demo-dev",
            "source_repo_url": repo.as_posix(),
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
    )

    html = render_operator_console(validation=result.validation, dry_run=result)

    assert "Generated Asset Preview" in html
    assert ".agent/reports/repository-analysis.md" in html
    assert "dockerfile-proposals/VALIDATION.md" in html
    assert "Jenkinsfile" in html
    assert "Validation Checklist" in html
    assert "Dockerfile proposals" in html
    assert "Namespace alignment" in html
    assert "Secret redaction" in html
    assert "Generated assets" in html
