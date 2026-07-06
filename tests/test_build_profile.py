from pathlib import Path

from k8s_deploy_agent.analyzer import analyze_repository
from k8s_deploy_agent.build_profile import BuildProfile
from k8s_deploy_agent.dockerfile_gate import evaluate_dockerfile_proposal_gate
from k8s_deploy_agent.dockerfile_proposal import (
    render_dockerfile_proposals,
    render_dockerignore_proposals,
    render_go_dockerfile,
    render_java_dockerfile,
    render_node_dockerfile,
    render_python_dockerfile,
)
from k8s_deploy_agent.dockerfile_validation import render_dockerfile_proposal_validation


def test_analyzer_creates_build_profiles_with_dependency_evidence(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (backend / "uv.lock").write_text("", encoding="utf-8")
    (backend / "Dockerfile").write_text("FROM python:3.12\nEXPOSE 8000\n", encoding="utf-8")
    app = backend / "app"
    app.mkdir()
    (app / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text(
        '{"scripts":{"build":"vite build","start":"vite --host 0.0.0.0 --port 3000"},"dependencies":{"vite":"latest"}}\n',
        encoding="utf-8",
    )
    (frontend / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")

    analysis = analyze_repository(tmp_path)

    profiles = {profile.service_name: profile for profile in analysis.build_profiles}
    assert set(profiles) == {"backend", "frontend"}

    backend_profile = profiles["backend"]
    assert isinstance(backend_profile, BuildProfile)
    assert backend_profile.app_type == "python"
    assert backend_profile.dependency_files == ("backend/requirements.txt",)
    assert backend_profile.lockfiles == ("backend/uv.lock",)
    assert backend_profile.build_tool == "uv"
    assert backend_profile.framework == "fastapi"
    assert backend_profile.runtime_command == "uvicorn backend.app.main:app --host 0.0.0.0"
    assert backend_profile.exposed_port == 8000
    assert backend_profile.docker_context == "backend"
    assert backend_profile.dockerfile_existing == "backend/Dockerfile"
    assert backend_profile.confidence == "confirmed"
    assert backend_profile.confirmed
    assert not backend_profile.unresolved_questions
    assert ("backend/requirements.txt", "dependency_files") in {
        (evidence.path, evidence.field) for evidence in backend_profile.evidence
    }
    assert evaluate_dockerfile_proposal_gate(backend_profile).allowed

    frontend_profile = profiles["frontend"]
    assert frontend_profile.app_type == "node"
    assert frontend_profile.dependency_files == ("frontend/package.json",)
    assert frontend_profile.lockfiles == ("frontend/pnpm-lock.yaml",)
    assert frontend_profile.build_tool == "pnpm"
    assert frontend_profile.framework == "vite"
    assert frontend_profile.runtime_command == "pnpm run start"
    assert frontend_profile.build_command == "pnpm run build"
    assert frontend_profile.build_output == "dist"
    assert frontend_profile.exposed_port == 3000
    assert "node_modules" in frontend_profile.ignore_candidates
    assert evaluate_dockerfile_proposal_gate(frontend_profile).allowed


def test_analyzer_detects_root_level_app_repository(tmp_path: Path):
    repo = tmp_path / "root-fastapi"
    repo.mkdir()
    (repo / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (repo / "Dockerfile").write_text("FROM python:3.12\nEXPOSE 8000\n", encoding="utf-8")
    app = repo / "app"
    app.mkdir()
    (app / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

    analysis = analyze_repository(repo)

    assert analysis.service_names == ["root-fastapi"]
    service = analysis.service("root-fastapi")
    assert service.path == repo
    assert service.dockerfile == repo / "Dockerfile"

    profile = analysis.build_profiles[0]
    assert profile.service_name == "root-fastapi"
    assert profile.service_path == "."
    assert profile.dependency_files == ("requirements.txt",)
    assert profile.docker_context == "."
    assert profile.dockerfile_existing == "Dockerfile"
    assert profile.runtime_command == "uvicorn app.main:app --host 0.0.0.0"
    assert profile.exposed_port == 8000
    assert profile.confirmed


def test_analyzer_creates_java_and_go_build_profiles(tmp_path: Path):
    api = tmp_path / "api"
    api.mkdir()
    (api / "pom.xml").write_text("<project />\n", encoding="utf-8")
    resources = api / "src/main/resources"
    resources.mkdir(parents=True)
    (resources / "application.properties").write_text("server.port=8081\n", encoding="utf-8")

    worker = tmp_path / "worker"
    worker.mkdir()
    (worker / "go.mod").write_text("module example.local/worker\n", encoding="utf-8")
    (worker / "go.sum").write_text("", encoding="utf-8")
    (worker / ".env").write_text("PORT=9090\n", encoding="utf-8")

    analysis = analyze_repository(tmp_path)

    profiles = {profile.service_name: profile for profile in analysis.build_profiles}
    assert profiles["api"].app_type == "java"
    assert profiles["api"].build_tool == "maven"
    assert profiles["api"].runtime_command == "java -jar app.jar"
    assert profiles["api"].build_command == "mvn -B package -DskipTests"
    assert profiles["api"].build_output == "target/*.jar"
    assert profiles["api"].exposed_port == 8081
    assert profiles["api"].confirmed
    assert profiles["api"].dependency_files == ("api/pom.xml",)
    assert "target" in profiles["api"].ignore_candidates

    assert analysis.service("worker").stack == "unsupported"
    assert profiles["worker"].app_type == "go"
    assert profiles["worker"].build_tool == "go"
    assert profiles["worker"].runtime_command == "/app"
    assert profiles["worker"].build_command == "CGO_ENABLED=0 go build -o /out/app ."
    assert profiles["worker"].build_output == "/out/app"
    assert profiles["worker"].exposed_port == 9090
    assert profiles["worker"].confirmed
    assert profiles["worker"].dependency_files == ("worker/go.mod",)
    assert profiles["worker"].lockfiles == ("worker/go.sum",)


def test_dockerfile_proposal_gate_blocks_low_confidence_and_unresolved_profiles():
    profile = BuildProfile(
        service_name="api",
        service_path="api",
        app_type="python",
        dependency_files=("api/requirements.txt",),
        build_tool="pip",
        runtime_command=None,
        exposed_port=None,
        confidence="low",
        unresolved_questions=("runtime command is not confirmed",),
    )

    gate = evaluate_dockerfile_proposal_gate(profile)

    assert not gate.allowed
    assert "profile confidence is low" in gate.reasons
    assert "runtime command is not confirmed" in gate.reasons
    assert "exposed port is not confirmed" in gate.reasons


def test_dockerfile_proposal_gate_allows_complete_profile():
    profile = BuildProfile(
        service_name="api",
        service_path="api",
        app_type="python",
        dependency_files=("api/requirements.txt",),
        build_tool="pip",
        runtime_command="uvicorn api.main:app --host 0.0.0.0",
        exposed_port=8000,
        confidence="medium",
    )

    gate = evaluate_dockerfile_proposal_gate(profile)

    assert gate.allowed
    assert gate.reasons == ()


def test_python_dockerfile_proposal_uses_service_context_and_review_artifact_path():
    profile = BuildProfile(
        service_name="backend",
        service_path="backend",
        app_type="python",
        dependency_files=("backend/requirements.txt",),
        build_tool="pip",
        runtime_command="uvicorn backend.app.main:app --host 0.0.0.0",
        docker_context="backend",
        exposed_port=8000,
        confidence="confirmed",
    )

    dockerfile = render_python_dockerfile(profile)
    proposals = render_dockerfile_proposals((profile,))

    assert proposals == {"backend/Dockerfile": dockerfile}
    assert "FROM python:3.12-slim AS runtime" in dockerfile
    assert "COPY requirements.txt ." in dockerfile
    assert "RUN pip install --no-cache-dir -r requirements.txt" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert 'CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000"]' in dockerfile


def test_multistack_dockerfile_and_dockerignore_proposals_are_review_only():
    node = BuildProfile(
        service_name="frontend",
        service_path="frontend",
        app_type="node",
        dependency_files=("frontend/package.json",),
        lockfiles=("frontend/pnpm-lock.yaml",),
        build_tool="pnpm",
        build_command="pnpm run build",
        runtime_command="pnpm run start",
        docker_context="frontend",
        ignore_candidates=("node_modules", "dist", ".env"),
        exposed_port=3000,
        confidence="confirmed",
    )
    java = BuildProfile(
        service_name="api",
        service_path="api",
        app_type="java",
        dependency_files=("api/pom.xml",),
        build_tool="maven",
        build_command="mvn -B package -DskipTests",
        build_output="target/*.jar",
        runtime_command="java -jar app.jar",
        docker_context="api",
        ignore_candidates=("target", ".env"),
        exposed_port=8080,
        confidence="confirmed",
    )
    go = BuildProfile(
        service_name="worker",
        service_path="worker",
        app_type="go",
        dependency_files=("worker/go.mod",),
        lockfiles=("worker/go.sum",),
        build_tool="go",
        build_command="CGO_ENABLED=0 go build -o /out/app .",
        build_output="/out/app",
        runtime_command="/app",
        docker_context="worker",
        ignore_candidates=("bin", ".env"),
        exposed_port=9090,
        confidence="confirmed",
    )

    node_dockerfile = render_node_dockerfile(node)
    java_dockerfile = render_java_dockerfile(java)
    go_dockerfile = render_go_dockerfile(go)
    proposals = {
        f"dockerfile-proposals/{path}": content
        for path, content in render_dockerfile_proposals((node, java, go)).items()
    }
    dockerignore_proposals = render_dockerignore_proposals((node, java, go))
    validation = render_dockerfile_proposal_validation((node, java, go), proposals)

    assert "RUN corepack enable && pnpm install --frozen-lockfile" in node_dockerfile
    assert "RUN pnpm run build" in node_dockerfile
    assert 'CMD ["sh", "-c", "pnpm run start -- --host 0.0.0.0 --port 3000"]' in node_dockerfile
    assert "COPY --from=build /workspace/target/*.jar app.jar" in java_dockerfile
    assert 'CMD ["java", "-jar", "app.jar"]' in java_dockerfile
    assert "RUN CGO_ENABLED=0 go build -o /out/app ." in go_dockerfile
    assert 'CMD ["/app"]' in go_dockerfile
    assert dockerignore_proposals["frontend/.dockerignore"].startswith("# Generated review-only")
    assert "node_modules" in dockerignore_proposals["frontend/.dockerignore"]
    assert "| Confidence gate | pass |" in validation
