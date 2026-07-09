from pathlib import Path

from k8s_deploy_agent.manifest_plan import (
    DependencyPlan,
    EnvVarPlan,
    PortCandidate,
    collect_dependency_plans,
    collect_env_var_plans,
    collect_port_candidates,
)
from k8s_deploy_agent.redaction import is_public_config_key, is_secret_key


def _candidate_map(candidates: tuple[PortCandidate, ...]) -> dict[tuple[str, str, int], PortCandidate]:
    return {
        (candidate.source, candidate.kind, candidate.value): candidate
        for candidate in candidates
    }


def _env_map(plans: tuple[EnvVarPlan, ...]) -> dict[str, EnvVarPlan]:
    return {plan.key: plan for plan in plans}


def _dependency_map(plans: tuple[DependencyPlan, ...]) -> dict[str, DependencyPlan]:
    return {plan.name: plan for plan in plans}


def test_port_analyzer_collects_dockerfile_expose_and_explicit_runtime_config(tmp_path: Path):
    service = tmp_path / "backend"
    service.mkdir()
    (service / "Dockerfile").write_text("FROM python:3.12\nEXPOSE 8000/tcp\n", encoding="utf-8")
    (service / ".env.example").write_text("PORT=9000\n", encoding="utf-8")
    app = service / "app"
    app.mkdir()
    (app / "main.py").write_text(
        "import uvicorn\nuvicorn.run('app.main:app', host='0.0.0.0', port=7000)\n",
        encoding="utf-8",
    )

    candidates = collect_port_candidates(
        tmp_path,
        service,
        runtime_command="uvicorn app.main:app --host 0.0.0.0 --port 9100",
        app_type="python",
    )
    by_key = _candidate_map(candidates)

    dockerfile = by_key[("dockerfile_expose", "container", 8000)]
    assert dockerfile.confidence == "confirmed"
    assert dockerfile.evidence_path == "backend/Dockerfile"

    env_port = by_key[("app_config", "config", 9000)]
    assert env_port.confidence == "confirmed"
    assert env_port.evidence_path == "backend/.env.example"

    python_port = by_key[("app_config", "config", 7000)]
    assert python_port.evidence_path == "backend/app/main.py"

    command_port = by_key[("runtime_command", "container", 9100)]
    assert command_port.confidence == "confirmed"
    assert command_port.evidence_path == "runtime_command"


def test_port_analyzer_splits_compose_host_and_container_ports(tmp_path: Path):
    api = tmp_path / "services" / "api"
    api.mkdir(parents=True)
    (tmp_path / "docker-compose.yml").write_text(
        """
services:
  api:
    ports:
      - "8080:8000"
    expose:
      - "8081"
    command: "uvicorn app.main:app --host 0.0.0.0 --port 8002"
  grafana:
    ports:
      - "3030:3000"
""",
        encoding="utf-8",
    )

    candidates = collect_port_candidates(tmp_path, api)
    by_key = _candidate_map(candidates)

    assert by_key[("compose_ports", "host", 8080)].confidence == "confirmed"
    assert by_key[("compose_ports", "container", 8000)].confidence == "confirmed"
    assert by_key[("compose_expose", "container", 8081)].evidence_path == "docker-compose.yml"
    assert by_key[("runtime_command", "container", 8002)].reason == "docker-compose service command port detected"
    assert ("compose_ports", "container", 8080) not in by_key
    assert ("compose_ports", "container", 3000) not in by_key


def test_port_analyzer_classifies_nginx_and_node_dev_server_ports(tmp_path: Path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "nginx.conf").write_text("server { listen 80; }\n", encoding="utf-8")
    (frontend / "package.json").write_text(
        '{"scripts":{"dev":"vite --host 0.0.0.0 --port 5173","start":"node server.js --port 3000"}}\n',
        encoding="utf-8",
    )
    (frontend / "vite.config.ts").write_text("export default { server: { port: 4173 } }\n", encoding="utf-8")

    candidates = collect_port_candidates(tmp_path, frontend, app_type="node")
    by_key = _candidate_map(candidates)

    nginx = by_key[("nginx_listen", "reverse_proxy", 80)]
    assert nginx.confidence == "confirmed"

    dev_script = by_key[("package_script", "dev_server", 5173)]
    assert dev_script.confidence == "inferred"

    start_script = by_key[("package_script", "container", 3000)]
    assert start_script.confidence == "confirmed"

    vite_config = by_key[("app_config", "dev_server", 4173)]
    assert vite_config.confidence == "inferred"


def test_redaction_public_helper_classifies_secret_and_public_config_keys():
    for key in (
        "TOKEN",
        "PASSWORD",
        "SECRET_KEY",
        "API_KEY",
        "PRIVATE_KEY",
        "ENCRYPTION_KEY",
        "AUTH_SECRET",
        "DATABASE_URL",
        "DATABASE_DIRECT_URL",
        "DSN",
        "CONNECTION_STRING",
        "WEBHOOK_SECRET",
        "CLIENT_SECRET",
        "ACCESS_KEY",
    ):
        assert is_secret_key(key)

    for key in ("NEXT_PUBLIC_API_URL", "VITE_BACKEND_URL", "PUBLIC_ASSET_BASE"):
        assert is_public_config_key(key)
        assert not is_secret_key(key)


def test_env_var_analyzer_collects_keys_without_values_and_classifies_categories(tmp_path: Path):
    (tmp_path / ".env.example").write_text(
        "ROOT_FEATURE_FLAG=true\nDATABASE_URL=postgres://user:password@db/app\n",
        encoding="utf-8",
    )
    service = tmp_path / "backend"
    service.mkdir()
    (service / ".env.example").write_text(
        "\n".join(
            [
                "APP_MODE=production",
                "SECRET_KEY=super-secret-value",
                "NEXT_PUBLIC_API_URL=https://public.example",
                "VITE_FEATURE_FLAG=enabled",
                "REDIS_URL=redis://localhost:6379",
            ]
        ),
        encoding="utf-8",
    )
    app = service / "app"
    app.mkdir()
    (app / "config.py").write_text(
        """
import os
from pydantic import BaseSettings

SMTP_HOST = os.getenv("SMTP_HOST")
OBJECT_STORE = os.environ["S3_ENDPOINT"]

class Settings(BaseSettings):
    API_KEY: str
    PUBLIC_SITE_NAME: str = "demo"
""",
        encoding="utf-8",
    )

    plans = collect_env_var_plans(tmp_path, service, app_type="python")
    by_key = _env_map(plans)

    assert by_key["ROOT_FEATURE_FLAG"].category == "configmap"
    assert by_key["ROOT_FEATURE_FLAG"].evidence_path == ".env.example"
    assert by_key["APP_MODE"].category == "configmap"
    assert by_key["SECRET_KEY"].category == "secret"
    assert by_key["DATABASE_URL"].category == "secret"
    assert by_key["REDIS_URL"].category == "dependency"
    assert by_key["NEXT_PUBLIC_API_URL"].category == "public_config"
    assert by_key["VITE_FEATURE_FLAG"].category == "public_config"
    assert by_key["SMTP_HOST"].category == "dependency"
    assert by_key["S3_ENDPOINT"].category == "dependency"
    assert by_key["API_KEY"].category == "secret"
    assert by_key["PUBLIC_SITE_NAME"].category == "public_config"

    rendered = "\n".join(f"{plan.key} {plan.category} {plan.evidence_path} {plan.reason}" for plan in plans)
    assert "super-secret-value" not in rendered
    assert "postgres://user:password@db/app" not in rendered
    assert "redis://localhost:6379" not in rendered
    assert "https://public.example" not in rendered


def test_dependency_analyzer_creates_manual_action_hints_from_env_and_compose(tmp_path: Path):
    service = tmp_path / "api"
    service.mkdir()
    (service / ".env.example").write_text(
        "\n".join(
            [
                "POSTGRES_SERVER=db",
                "POSTGRES_PASSWORD=not-output",
                "REDIS_URL=redis://cache",
                "SMTP_HOST=smtp.internal",
                "S3_ENDPOINT=http://minio:9000",
                "AWS_ACCESS_KEY_ID=minio",
                "OPENAI_API_KEY=not-output",
                "AZURE_OPENAI_ENDPOINT=https://azure.example",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "docker-compose.yml").write_text(
        """
services:
  api:
    environment:
      MYSQL_HOST: mysql
      MONGODB_URI: mongodb://mongo/app
  postgres:
    image: postgres:16
  redis:
    image: redis:7
""",
        encoding="utf-8",
    )

    dependencies = collect_dependency_plans(tmp_path, service)
    by_name = _dependency_map(dependencies)

    assert by_name["postgres"].kind == "postgres"
    assert by_name["postgres"].action == "manual-required"
    assert by_name["redis"].kind == "redis"
    assert by_name["mysql"].kind == "mysql"
    assert by_name["mongodb"].kind == "mongodb"
    assert by_name["smtp"].kind == "smtp"
    assert by_name["object_storage"].kind == "object_storage"
    assert by_name["external_api"].kind == "external_api"
    assert "OPENAI_API_KEY" in by_name["external_api"].reason

    rendered = "\n".join(f"{plan.name} {plan.kind} {plan.evidence_path} {plan.reason}" for plan in dependencies)
    assert "not-output" not in rendered
    assert "mongodb://mongo/app" not in rendered
    assert "https://azure.example" not in rendered
