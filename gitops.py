from __future__ import annotations

from k8s_deploy_agent.analyzer import RepositoryAnalysis
from k8s_deploy_agent.config import DemoConfig
from k8s_deploy_agent.manifest_plan import WorkloadManifestPlan, build_workload_manifest_plans


def render_gitops_manifests(
    config: DemoConfig,
    analysis: RepositoryAnalysis,
    image_tag: str,
) -> dict[str, str]:
    manifests = {
        "fleet.yaml": _fleet_yaml(config),
        "base/namespace.yaml": _namespace_yaml(config),
    }

    manifest_plan = build_workload_manifest_plans(config, analysis, image_tag)
    for workload in manifest_plan.confirmed:
        base_path = f"apps/{workload.service_name}"
        manifests[f"{base_path}/deployment.yaml"] = _deployment_yaml(config, workload)
        manifests[f"{base_path}/service.yaml"] = _service_yaml(config, workload)
        manifests[f"{base_path}/configmap.yaml"] = _configmap_yaml(config, workload)

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


def _deployment_yaml(config: DemoConfig, workload: WorkloadManifestPlan) -> str:
    name = _resource_name(config, workload)
    port = workload.container_port.value
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
        - name: {workload.service_name}
          image: {workload.image}
          ports:
            - containerPort: {port}
          envFrom:
            - configMapRef:
                name: {name}-config
"""


def _service_yaml(config: DemoConfig, workload: WorkloadManifestPlan) -> str:
    name = _resource_name(config, workload)
    port = workload.container_port.value
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
    - port: {port}
      targetPort: {port}
"""


def _configmap_yaml(config: DemoConfig, workload: WorkloadManifestPlan) -> str:
    name = _resource_name(config, workload)
    return f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: {name}-config
  namespace: {config.namespace}
data: {{}}
"""


def _resource_name(config: DemoConfig, workload: WorkloadManifestPlan) -> str:
    return f"{config.app_name}-{workload.service_name}"