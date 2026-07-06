from pathlib import Path

from k8s_deploy_agent.cli import main


def write_sample_repo(root: Path) -> Path:
    repo = root / "sample-repo"
    backend = repo / "backend"
    backend.mkdir(parents=True)
    (backend / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (backend / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")

    frontend = repo / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text("{}\n", encoding="utf-8")
    (frontend / "Dockerfile").write_text("FROM node:22\n", encoding="utf-8")
    return repo


def write_config(root: Path) -> Path:
    config = root / "demo-inputs.yaml"
    config.write_text(
        "\n".join(
            [
                'source_repo_url: "https://gitea.example.local/team/source.git"',
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
    assert (output / "Jenkinsfile").is_file()
    assert (output / ".agent/reports/repository-analysis.md").is_file()
    assert (output / "gitops/fleet.yaml").is_file()
    assert (output / "gitops/apps/backend/deployment.yaml").is_file()
    assert (output / "gitops/apps/frontend/deployment.yaml").is_file()

    jenkinsfile = (output / "Jenkinsfile").read_text(encoding="utf-8")
    assert "podTemplate(" in jenkinsfile
    assert "Build and Push Images" in jenkinsfile
    assert "Update GitOps Repository" in jenkinsfile
