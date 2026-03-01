"""User model for k8s-iam-operator."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict


class UserType(str, Enum):
    """Type of user identity."""
    HUMAN = "human"
    SERVICE_ACCOUNT = "serviceAccount"


class NetworkPolicyMode(str, Enum):
    """Network policy mode for user namespace."""
    NONE = "none"
    ISOLATED = "isolated"
    RESTRICTED = "restricted"


@dataclass
class ResourceQuota:
    """Resource quota configuration for user namespace."""
    cpu: Optional[str] = None
    memory: Optional[str] = None
    pods: Optional[str] = None
    services: Optional[str] = None
    persistentvolumeclaims: Optional[str] = None
    secrets: Optional[str] = None
    configmaps: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ResourceQuota":
        """Create a ResourceQuota from a dictionary."""
        return cls(
            cpu=data.get("cpu"),
            memory=data.get("memory"),
            pods=data.get("pods"),
            services=data.get("services"),
            persistentvolumeclaims=data.get("persistentvolumeclaims"),
            secrets=data.get("secrets"),
            configmaps=data.get("configmaps"),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in {
            "cpu": self.cpu,
            "memory": self.memory,
            "pods": self.pods,
            "services": self.services,
            "persistentvolumeclaims": self.persistentvolumeclaims,
            "secrets": self.secrets,
            "configmaps": self.configmaps,
        }.items() if v is not None}

    def is_empty(self) -> bool:
        """Check if all quota values are None."""
        return all(v is None for v in [
            self.cpu, self.memory, self.pods, self.services,
            self.persistentvolumeclaims, self.secrets, self.configmaps
        ])


@dataclass
class NamespaceConfig:
    """Configuration for user's dedicated namespace."""
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    quota: Optional[ResourceQuota] = None
    network_policy: NetworkPolicyMode = NetworkPolicyMode.NONE

    @classmethod
    def from_dict(cls, data: dict) -> "NamespaceConfig":
        """Create a NamespaceConfig from a dictionary."""
        quota_data = data.get("quota")
        return cls(
            labels=data.get("labels", {}),
            annotations=data.get("annotations", {}),
            quota=ResourceQuota.from_dict(quota_data) if quota_data else None,
            network_policy=NetworkPolicyMode(data.get("networkPolicy", "none")),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format matching CRD spec."""
        result = {
            "labels": self.labels,
            "annotations": self.annotations,
            "networkPolicy": self.network_policy.value,
        }
        if self.quota and not self.quota.is_empty():
            result["quota"] = self.quota.to_dict()
        return result


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
    # New explicit type field
    user_type: UserType = UserType.SERVICE_ACCOUNT

    # Legacy field (deprecated, use user_type instead)
    enabled: bool = False

    # Target namespace for serviceAccount type
    target_namespace: Optional[str] = None

    # Namespace configuration for human users
    namespace_config: Optional[NamespaceConfig] = None

    # RBAC bindings
    cluster_roles: List[ClusterRoleBinding] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "UserSpec":
        """Create a UserSpec from a dictionary."""
        croles = data.get("CRoles", [])

        # Determine user type (new field takes precedence over legacy enabled)
        user_type_str = data.get("type")
        enabled = data.get("enabled", False)

        if user_type_str:
            user_type = UserType(user_type_str)
        elif enabled:
            # Legacy: enabled=true means human user
            user_type = UserType.HUMAN
        else:
            user_type = UserType.SERVICE_ACCOUNT

        # Parse namespace config
        ns_config_data = data.get("namespaceConfig")
        namespace_config = NamespaceConfig.from_dict(ns_config_data) if ns_config_data else None

        return cls(
            user_type=user_type,
            enabled=enabled,
            target_namespace=data.get("targetNamespace"),
            namespace_config=namespace_config,
            cluster_roles=[ClusterRoleBinding.from_dict(cr) for cr in croles],
            roles=data.get("Roles", []),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format matching CRD spec."""
        result = {
            "type": self.user_type.value,
            "enabled": self.enabled,
            "CRoles": [cr.to_dict() for cr in self.cluster_roles],
            "Roles": self.roles,
        }
        if self.target_namespace:
            result["targetNamespace"] = self.target_namespace
        if self.namespace_config:
            result["namespaceConfig"] = self.namespace_config.to_dict()
        return result

    def get_namespaces(self) -> List[str]:
        """Get all namespaces from cluster role bindings."""
        return [cr.namespace for cr in self.cluster_roles if cr.namespace]

    @property
    def is_human(self) -> bool:
        """Check if this is a human user (needs namespace + kubeconfig)."""
        return self.user_type == UserType.HUMAN or self.enabled

    @property
    def is_service_account(self) -> bool:
        """Check if this is a service account user."""
        return not self.is_human


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

    @property
    def sa_namespace(self) -> str:
        """Get the namespace where ServiceAccount should be created.

        For human users: same as User CR namespace (operator namespace)
        For service accounts: targetNamespace or User CR namespace
        """
        if self.spec.is_human:
            return self.namespace
        return self.spec.target_namespace or self.namespace

    @property
    def quota_name(self) -> str:
        """Get the ResourceQuota name for this user's namespace."""
        return f"{self.name}-quota"

    @property
    def network_policy_name(self) -> str:
        """Get the NetworkPolicy name for this user's namespace."""
        return f"{self.name}-network-policy"
