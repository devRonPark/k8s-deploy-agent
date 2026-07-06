from __future__ import annotations

from k8s_deploy_agent.analyzer import RepositoryAnalysis, ServiceCandidate
from k8s_deploy_agent.config import DemoConfig
from k8s_deploy_agent.gitops import render_gitops_manifests


def render_jenkinsfile(config: DemoConfig, analysis: RepositoryAnalysis) -> str:
    services = [service for service in analysis.services if service.dockerfile and service.stack != "unsupported"]
    build_commands = "\n".join(_kaniko_command(config, analysis, service) for service in services)
    manifest_commands = _manifest_write_commands(config, analysis)
    authed_gitops_url = config.gitops_repo_url.replace(
        "://", "://${GITOPS_USER}:${GITOPS_TOKEN}@", 1
    )

    # Check if registry information is provided
    if config.registry_credential_id and config.registry_ca_cert_credential_id:
        # Use registry credentials if available
        registry_section = f"""        withCredentials([
          usernamePassword(credentialsId: '{config.registry_credential_id}', usernameVariable: 'REGISTRY_USER', passwordVariable: 'REGISTRY_PASSWORD'),
          file(credentialsId: '{config.registry_ca_cert_credential_id}', variable: 'REGISTRY_CA_CERT')
        ]) {{
          sh '''
            set -eu
            mkdir -p /kaniko/ssl/certs /kaniko/.docker
            cp "$REGISTRY_CA_CERT" /kaniko/ssl/certs/registry-ca.crt
            REGISTRY_AUTH=$(printf '%s:%s' "$REGISTRY_USER" "$REGISTRY_PASSWORD" | base64 | tr -d '\\n')
            printf '{{"auths":{{"%s":{{"auth":"%s"}}}}}}' '{config.registry_url}' "$REGISTRY_AUTH" > /kaniko/.docker/config.json
            {build_commands}
          '''
        }}"""
    else:
        # Use simplified build commands without registry authentication
        registry_section = f"""        sh '''
            set -eu
            {build_commands}
          '''"""

    return f"""podTemplate(
  containers: [
    containerTemplate(name: 'kaniko', image: 'gcr.io/kaniko-project/executor:debug', command: 'sleep', args: '99d'),
    containerTemplate(name: 'git', image: 'alpine/git:latest', command: 'sleep', args: '99d')
  ]
) {{
  node(POD_LABEL) {{
    stage('Checkout Source') {{
      checkout scm
    }}

    stage('Build and Push Images') {{
      container('kaniko') {{
        {registry_section}
      }}
    }}

    stage('Update GitOps Repository') {{
      container('git') {{
        withCredentials([
          usernamePassword(credentialsId: '{config.gitops_credential_id}', usernameVariable: 'GITOPS_USER', passwordVariable: 'GITOPS_TOKEN')
        ]) {{
          sh '''
            set -eu
            git clone --branch {config.gitops_branch} {authed_gitops_url} gitops-repo
            cd gitops-repo
            git config user.email "k8s-deploy-agent@example.local"
            git config user.name "k8s-deploy-agent"
            {manifest_commands}
            git add {config.gitops_path}
            git commit -m "Update {config.app_name} images ${{BUILD_NUMBER}}"
            git push origin {config.gitops_branch}
          '''
        }}
      }}
    }}
  }}
}}
"""


def _kaniko_command(config: DemoConfig, analysis: RepositoryAnalysis, service: ServiceCandidate) -> str:
    assert service.dockerfile is not None
    dockerfile = service.dockerfile.relative_to(analysis.root).as_posix()
    context = service.path.relative_to(analysis.root).as_posix()
    destination = config.image_for(service.name, "${BUILD_NUMBER}")
    return (
        "            /kaniko/executor "
        f"--context=${{WORKSPACE}}/{context} "
        f"--dockerfile=${{WORKSPACE}}/{dockerfile} "
        f"--destination={destination}"
    )


def _manifest_write_commands(config: DemoConfig, analysis: RepositoryAnalysis) -> str:
    # ponytail: 매 빌드마다 manifest 전체 overwrite — image tag만 갱신하는 sed 방식은
    # GitOps repo를 사람이 직접 수정하기 시작하는 시점에 도입
    manifests = render_gitops_manifests(config, analysis, image_tag="${BUILD_NUMBER}")
    blocks: list[str] = []
    for name, content in manifests.items():
        path = f"{config.gitops_path}/{name}"
        directory = path.rsplit("/", 1)[0]
        blocks.append(
            f"            mkdir -p {directory}\n"
            f"            cat > {path} <<EOF\n"
            f"{content.rstrip()}\n"
            "EOF"
        )
    return "\n".join(blocks)
