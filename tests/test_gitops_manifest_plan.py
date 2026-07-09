from pathlib import Path

from k8s_deploy_agent.analyzer import analyze_repository
from k8s_deploy_agent.config import DemoConfig
from k8s_deploy_agent.gitops import render_gitops_manifests


def _demo_config() -> DemoConfig:
    return DemoConfig(
        source_repo_url="https://example.com/app.git",
        source_branch="main",
        source_credential_id="cred-source",
        gitops_repo_url="https://example.com/gitops.git",
        gitops_branch="main",
        gitops_path="apps",
        gitops_credential_id="cred-gitops",
        app_name="demo",
        environment="dev",
    )


def test_gitops_renders_confirmed_workload_with_evidence_based_container_port(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (backend / "uv.lock").write_text("", encoding="utf-8")
    (backend / "Dockerfile").write_text("FROM python:3.12\nEXPOSE 8000\n", encoding="utf-8")
    app = backend / "app"
    app.mkdir()
    (app / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

    analysis = analyze_repository(tmp_path)
    config = _demo_config()
    manifests = render_gitops_manifests(config, analysis, image_tag="sha-123")

    assert "fleet.yaml" in manifests
    assert "base/namespace.yaml" in manifests

    deployment = manifests["apps/backend/deployment.yaml"]
    assert "containerPort: 8000" in deployment
    assert f"image: {config.image_for('backend', 'sha-123')}" in deployment

    service = manifests["apps/backend/service.yaml"]
    assert "port: 8000" in service
    assert "targetPort: 8000" in service

    assert "apps/backend/configmap.yaml" in manifests


def test_gitops_skips_unconfirmed_service_without_port_evidence(tmp_path: Path):
    worker = tmp_path / "worker"
    worker.mkdir()
    (worker / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (worker / "uv.lock").write_text("", encoding="utf-8")
    (worker / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")
    app = worker / "app"
    app.mkdir()
    (app / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

    analysis = analyze_repository(tmp_path)
    manifests = render_gitops_manifests(_demo_config(), analysis, image_tag="sha-123")

    assert "apps/worker/deployment.yaml" not in manifests
    assert "apps/worker/service.yaml" not in manifests
    assert "apps/worker/configmap.yaml" not in manifests
    assert "fleet.yaml" in manifests
    assert "base/namespace.yaml" in manifests


def test_gitops_only_renders_confirmed_services_among_mixed_set(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (backend / "uv.lock").write_text("", encoding="utf-8")
    (backend / "Dockerfile").write_text("FROM python:3.12\nEXPOSE 8000\n", encoding="utf-8")
    (backend / "app").mkdir()
    (backend / "app" / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8"
    )

    worker = tmp_path / "worker"
    worker.mkdir()
    (worker / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (worker / "uv.lock").write_text("", encoding="utf-8")
    (worker / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")
    (worker / "app").mkdir()
    (worker / "app" / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8"
    )

    analysis = analyze_repository(tmp_path)
    manifests = render_gitops_manifests(_demo_config(), analysis, image_tag="sha-123")

    assert "apps/backend/deployment.yaml" in manifests
    assert "apps/worker/deployment.yaml" not in manifests
