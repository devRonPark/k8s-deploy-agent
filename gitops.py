from __future__ import annotations

from k8s_deploy_agent.analyzer import RepositoryAnalysis, ServiceCandidate
from k8s_deploy_agent.config import DemoConfig


def render_gitops_manifests(
    config: DemoConfig,
    analysis: RepositoryAnalysis,
    image_tag: str,
) -> dict[str, str]:
    manifests = {
        "fleet.yaml": _fleet_yaml(config),
        "base/namespace.yaml": _namespace_yaml(config),
    }

    for service in analysis.services:
        if service.stack == "unsupported" or not service.dockerfile:
            continue
        base_path = f"apps/{service.name}"
        manifests[f"{base_path}/deployment.yaml"] = _deployment_yaml(config, service, image_tag)
        manifests[f"{base_path}/service.yaml"] = _service_yaml(config, service)
        manifests[f"{base_path}/configmap.yaml"] = _configmap_yaml(config, service)

    return manifests


def _fleet_yaml(config: DemoConfig) -> str:
    return f"""defaultNamespace: {config.namespace}
namespace: {config.namespace}
"""


def _namespace_yaml(config: DemoConfig) -> str:
    return f"""apiVersion: v1
kind: Namespace
metadata:
  name: {config.namespace}
"""


def _deployment_yaml(config: DemoConfig, service: ServiceCandidate, image_tag: str) -> str:
    name = _resource_name(config, service)
    return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {config.namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
        - name: {service.name}
          image: {config.image_for(service.name, image_tag)}
          ports:
            - containerPort: 80
          envFrom:
            - configMapRef:
                name: {name}-config
"""


def _service_yaml(config: DemoConfig, service: ServiceCandidate) -> str:
    name = _resource_name(config, service)
    return f"""apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: {config.namespace}
spec:
  type: ClusterIP
  selector:
    app: {name}
  ports:
    - port: 80
      targetPort: 80
"""


def _configmap_yaml(config: DemoConfig, service: ServiceCandidate) -> str:
    name = _resource_name(config, service)
    return f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: {name}-config
  namespace: {config.namespace}
data: {{}}
"""


def _resource_name(config: DemoConfig, service: ServiceCandidate) -> str:
    return f"{config.app_name}-{service.name}"