"""Group model for k8s-iam-operator."""

from dataclasses import dataclass, field
from typing import List, Optional

from app.models.user import ClusterRoleBinding


@dataclass
class GroupSpec:
    """Represents the spec of a Group CRD."""
    cluster_roles: List[ClusterRoleBinding] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "GroupSpec":
        """Create a GroupSpec from a dictionary."""
        croles = data.get("CRoles", [])
        return cls(
            cluster_roles=[ClusterRoleBinding.from_dict(cr) for cr in croles],
            roles=data.get("Roles", []),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format matching CRD spec."""
        return {
            "CRoles": [cr.to_dict() for cr in self.cluster_roles],
            "Roles": self.roles,
        }

    def get_namespaces(self) -> List[str]:
        """Get all namespaces from cluster role bindings."""
        return [cr.namespace for cr in self.cluster_roles if cr.namespace]

    def get_cluster_wide_roles(self) -> List[ClusterRoleBinding]:
        """Get cluster role bindings without namespace (cluster-wide)."""
        return [cr for cr in self.cluster_roles if not cr.namespace]

    def get_namespaced_roles(self) -> List[ClusterRoleBinding]:
        """Get cluster role bindings with namespace."""
        return [cr for cr in self.cluster_roles if cr.namespace]


@dataclass
class Group:
    """Represents a Group CRD resource."""
    name: str
    namespace: str
    spec: GroupSpec
    uid: Optional[str] = None
    resource_version: Optional[str] = None
    labels: dict = field(default_factory=dict)
    annotations: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: dict) -> "Group":
        """Create a Group from a Kopf body dictionary."""
        metadata = body.get("metadata", {})
        spec_data = body.get("spec", {})
        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace", ""),
            spec=GroupSpec.from_dict(spec_data),
            uid=metadata.get("uid"),
            resource_version=metadata.get("resourceVersion"),
            labels=metadata.get("labels", {}),
            annotations=metadata.get("annotations", {}),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "apiVersion": "k8sio.auth/v1",
            "kind": "Group",
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

    def role_binding_name(self, namespace: str, role: str) -> str:
        """Generate RoleBinding name for a namespaced role."""
        return f"{self.name}-{namespace}-{role}"

    def cluster_role_binding_name(self, role: str) -> str:
        """Generate ClusterRoleBinding name for a cluster-wide role."""
        return f"{self.name}-{self.namespace}-{role}"
