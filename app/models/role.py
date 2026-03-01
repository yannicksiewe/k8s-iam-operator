"""Role and ClusterRole models for k8s-iam-operator."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PolicyRule:
    """Represents a Kubernetes RBAC policy rule."""
    api_groups: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    verbs: List[str] = field(default_factory=list)
    resource_names: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyRule":
        """Create a PolicyRule from a dictionary."""
        return cls(
            api_groups=data.get("apiGroups", []),
            resources=data.get("resources", []),
            verbs=data.get("verbs", []),
            resource_names=data.get("resourceNames"),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format matching K8s API."""
        result = {
            "apiGroups": self.api_groups,
            "resources": self.resources,
            "verbs": self.verbs,
        }
        if self.resource_names is not None:
            result["resourceNames"] = self.resource_names
        return result


@dataclass
class RoleSpec:
    """Represents the spec of a Role or ClusterRole CRD."""
    rules: List[PolicyRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "RoleSpec":
        """Create a RoleSpec from a dictionary."""
        rules_data = data.get("rules", [])
        return cls(
            rules=[PolicyRule.from_dict(r) for r in rules_data]
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format matching CRD spec."""
        return {
            "rules": [r.to_dict() for r in self.rules]
        }


@dataclass
class Role:
    """Represents a Role CRD resource (namespaced)."""
    name: str
    namespace: str
    spec: RoleSpec
    uid: Optional[str] = None
    resource_version: Optional[str] = None
    labels: dict = field(default_factory=dict)
    annotations: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: dict) -> "Role":
        """Create a Role from a Kopf body dictionary."""
        metadata = body.get("metadata", {})
        spec_data = body.get("spec", {})
        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace", ""),
            spec=RoleSpec.from_dict(spec_data),
            uid=metadata.get("uid"),
            resource_version=metadata.get("resourceVersion"),
            labels=metadata.get("labels", {}),
            annotations=metadata.get("annotations", {}),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "apiVersion": "k8sio.auth/v1",
            "kind": "Role",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace,
                "uid": self.uid,
                "resourceVersion": self.resource_version,
                "labels": self.labels,
                "annotations": self.annotations,
            },
            "spec": self.spec.to_dict(),
        }


@dataclass
class ClusterRole:
    """Represents a ClusterRole CRD resource (cluster-scoped)."""
    name: str
    spec: RoleSpec
    uid: Optional[str] = None
    resource_version: Optional[str] = None
    labels: dict = field(default_factory=dict)
    annotations: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: dict) -> "ClusterRole":
        """Create a ClusterRole from a Kopf body dictionary."""
        metadata = body.get("metadata", {})
        spec_data = body.get("spec", {})
        return cls(
            name=metadata.get("name", ""),
            spec=RoleSpec.from_dict(spec_data),
            uid=metadata.get("uid"),
            resource_version=metadata.get("resourceVersion"),
            labels=metadata.get("labels", {}),
            annotations=metadata.get("annotations", {}),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "apiVersion": "k8sio.auth/v1",
            "kind": "ClusterRole",
            "metadata": {
                "name": self.name,
                "uid": self.uid,
                "resourceVersion": self.resource_version,
                "labels": self.labels,
                "annotations": self.annotations,
            },
            "spec": self.spec.to_dict(),
        }
