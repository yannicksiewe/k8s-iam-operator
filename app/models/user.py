"""User model for k8s-iam-operator."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ClusterRoleBinding:
    """Represents a cluster role binding in a User or Group spec."""
    cluster_role: str
    namespace: Optional[str] = None
    group: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ClusterRoleBinding":
        """Create a ClusterRoleBinding from a dictionary."""
        return cls(
            cluster_role=data.get("clusterRole", ""),
            namespace=data.get("namespace"),
            group=data.get("group"),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format matching CRD spec."""
        result = {"clusterRole": self.cluster_role}
        if self.namespace:
            result["namespace"] = self.namespace
        if self.group:
            result["group"] = self.group
        return result

    def binding_name(self, user_name: str) -> str:
        """Generate the RoleBinding name for this binding."""
        if self.namespace:
            return f"{user_name}-{self.namespace}-{self.cluster_role}"
        return f"{user_name}-{self.cluster_role}"


@dataclass
class UserSpec:
    """Represents the spec of a User CRD."""
    enabled: bool = False
    cluster_roles: List[ClusterRoleBinding] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "UserSpec":
        """Create a UserSpec from a dictionary."""
        croles = data.get("CRoles", [])
        return cls(
            enabled=data.get("enabled", False),
            cluster_roles=[ClusterRoleBinding.from_dict(cr) for cr in croles],
            roles=data.get("Roles", []),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format matching CRD spec."""
        return {
            "enabled": self.enabled,
            "CRoles": [cr.to_dict() for cr in self.cluster_roles],
            "Roles": self.roles,
        }

    def get_namespaces(self) -> List[str]:
        """Get all namespaces from cluster role bindings."""
        return [cr.namespace for cr in self.cluster_roles if cr.namespace]


@dataclass
class User:
    """Represents a User CRD resource."""
    name: str
    namespace: str
    spec: UserSpec
    uid: Optional[str] = None
    resource_version: Optional[str] = None
    labels: dict = field(default_factory=dict)
    annotations: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: dict) -> "User":
        """Create a User from a Kopf body dictionary."""
        metadata = body.get("metadata", {})
        spec_data = body.get("spec", {})
        return cls(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace", ""),
            spec=UserSpec.from_dict(spec_data),
            uid=metadata.get("uid"),
            resource_version=metadata.get("resourceVersion"),
            labels=metadata.get("labels", {}),
            annotations=metadata.get("annotations", {}),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "apiVersion": "k8sio.auth/v1",
            "kind": "User",
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

    @property
    def service_account_name(self) -> str:
        """Get the service account name for this user."""
        return self.name

    @property
    def token_secret_name(self) -> str:
        """Get the token secret name for this user."""
        return f"{self.name}-token"

    @property
    def kubeconfig_secret_name(self) -> str:
        """Get the kubeconfig secret name for this user."""
        return f"{self.name}-cluster-config"

    @property
    def restricted_role_name(self) -> str:
        """Get the restricted namespace role name for this user."""
        return f"{self.name}-restricted-namespace-role"

    @property
    def restricted_binding_name(self) -> str:
        """Get the restricted namespace binding name for this user."""
        return f"{self.name}-restricted-namespace-binding"

    @property
    def user_namespace(self) -> str:
        """Get the dedicated namespace for this user (same as user name)."""
        return self.name
