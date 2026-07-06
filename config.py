from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


REQUIRED_FIELDS = (
    "source_repo_url",
    "source_branch",
    "source_credential_id",
    "gitops_repo_url",
    "gitops_branch",
    "gitops_path",
    "gitops_credential_id",
    "app_name",
    "environment",
)


@dataclass(frozen=True)
class DemoConfig:
    source_repo_url: str
    source_branch: str
    source_credential_id: str
    gitops_repo_url: str
    gitops_branch: str
    gitops_path: str
    gitops_credential_id: str
    app_name: str
    environment: str
    registry_url: Optional[str] = None
    registry_project: Optional[str] = None
    registry_credential_id: Optional[str] = None
    registry_ca_cert_credential_id: Optional[str] = None
    target_namespace: str | None = None

    @classmethod
    def from_mapping(cls, values: dict[str, Any]) -> "DemoConfig":
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field, "")).strip()]
        if missing:
            missing_list = ", ".join(missing)
            raise ValueError(f"Missing required config fields: {missing_list}")

        data = {field: str(values[field]).strip() for field in REQUIRED_FIELDS}
        # Handle optional registry fields
        optional_fields = ["registry_url", "registry_project", "registry_credential_id", "registry_ca_cert_credential_id"]
        for field in optional_fields:
            data[field] = str(values.get(field, "")).strip() or None
        target_namespace = str(values.get("target_namespace", "")).strip() or None
        return cls(**data, target_namespace=target_namespace)

    @property
    def namespace(self) -> str:
        if self.target_namespace:
            return self.target_namespace
        return f"{self.app_name}-{self.environment}"

    def image_for(self, service_name: str, image_tag: str) -> str:
        # If registry information is not provided, return a generic image name
        if self.registry_url and self.registry_project:
            return (
                f"{self.registry_url}/{self.registry_project}/"
                f"{self.app_name}-{service_name}:{image_tag}"
            )
        else:
            # Return a generic image name without registry prefix
            return f"{self.app_name}-{service_name}:{image_tag}"


def load_demo_config(path: str | Path) -> DemoConfig:
    # ponytail: flat "key: value"(yaml) 또는 "KEY=VALUE"(.env)만 지원 — 중첩 필요 시 pyyaml
    values: dict[str, Any] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        positions = [index for index in (line.find("="), line.find(":")) if index >= 0]
        if not positions:
            continue
        separator = min(positions)
        key, value = line[:separator], line[separator + 1 :]
        values[key.strip().lower()] = value.strip().strip("'\"")
    return DemoConfig.from_mapping(values)
