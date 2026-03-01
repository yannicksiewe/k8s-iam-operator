"""Protocol definitions for k8s-iam-operator.

This module defines Protocol classes (structural subtyping) for the repository
layer and services. Using protocols enables better type checking and easier
testing through dependency injection.
"""

from typing import Protocol, List, Optional, Dict, Any, runtime_checkable


@runtime_checkable
class INamespaceRepository(Protocol):
    """Protocol for namespace operations."""

    def get(self, name: str) -> Any:
        """Get a namespace by name."""
        ...

    def exists(self, name: str) -> bool:
        """Check if a namespace exists."""
        ...

    def create(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None
    ) -> Any:
        """Create a namespace."""
        ...

    def delete(self, name: str, grace_period_seconds: int = 0) -> None:
        """Delete a namespace."""
        ...

    def list_all(self) -> List[Any]:
        """List all namespaces."""
        ...

    def list_names(self) -> List[str]:
        """List all namespace names."""
        ...

    def ensure_exists(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None
    ) -> Any:
        """Ensure a namespace exists, creating it if necessary."""
        ...


@runtime_checkable
class IServiceAccountRepository(Protocol):
    """Protocol for service account operations."""

    def get(self, name: str, namespace: str) -> Any:
        """Get a service account by name and namespace."""
        ...

    def exists(self, name: str, namespace: str) -> bool:
        """Check if a service account exists."""
        ...

    def create(
        self,
        name: str,
        namespace: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        automount_token: bool = True
    ) -> Any:
        """Create a service account."""
        ...

    def update(
        self,
        name: str,
        namespace: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None
    ) -> Any:
        """Update a service account."""
        ...

    def delete(self, name: str, namespace: str, grace_period_seconds: int = 5) -> None:
        """Delete a service account."""
        ...

    def list_in_namespace(self, namespace: str) -> List[Any]:
        """List all service accounts in a namespace."""
        ...

    def ensure_exists(
        self,
        name: str,
        namespace: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        automount_token: bool = True
    ) -> Any:
        """Ensure a service account exists, creating it if necessary."""
        ...


@runtime_checkable
class ISecretRepository(Protocol):
    """Protocol for secret operations."""

    def get(self, name: str, namespace: str) -> Any:
        """Get a secret by name and namespace."""
        ...

    def exists(self, name: str, namespace: str) -> bool:
        """Check if a secret exists."""
        ...

    def create(
        self,
        name: str,
        namespace: str,
        data: Dict[str, str],
        secret_type: str = "Opaque",
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None
    ) -> Any:
        """Create a secret."""
        ...

    def create_service_account_token(
        self,
        sa_name: str,
        namespace: str,
        token_name: Optional[str] = None
    ) -> Any:
        """Create a service account token secret."""
        ...

    def create_kubeconfig_secret(
        self,
        name: str,
        namespace: str,
        kubeconfig_data: str
    ) -> Any:
        """Create a kubeconfig secret."""
        ...

    def update(
        self,
        name: str,
        namespace: str,
        data: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None
    ) -> Any:
        """Update a secret."""
        ...

    def delete(self, name: str, namespace: str) -> None:
        """Delete a secret."""
        ...

    def list_in_namespace(
        self,
        namespace: str,
        label_selector: Optional[str] = None
    ) -> List[Any]:
        """List secrets in a namespace."""
        ...


@runtime_checkable
class IRBACRepository(Protocol):
    """Protocol for RBAC operations."""

    # Role operations
    def get_role(self, name: str, namespace: str) -> Any:
        """Get a Role by name and namespace."""
        ...

    def role_exists(self, name: str, namespace: str) -> bool:
        """Check if a role exists."""
        ...

    def create_role(
        self,
        name: str,
        namespace: str,
        rules: List[Dict[str, Any]],
        labels: Optional[Dict[str, str]] = None
    ) -> Any:
        """Create a Role."""
        ...

    def update_role(self, name: str, namespace: str, rules: List[Dict[str, Any]]) -> Any:
        """Update a Role."""
        ...

    def delete_role(self, name: str, namespace: str) -> None:
        """Delete a Role."""
        ...

    # ClusterRole operations
    def get_cluster_role(self, name: str) -> Any:
        """Get a ClusterRole by name."""
        ...

    def cluster_role_exists(self, name: str) -> bool:
        """Check if a ClusterRole exists."""
        ...

    def create_cluster_role(
        self,
        name: str,
        rules: List[Dict[str, Any]],
        labels: Optional[Dict[str, str]] = None
    ) -> Any:
        """Create a ClusterRole."""
        ...

    def update_cluster_role(self, name: str, rules: List[Dict[str, Any]]) -> Any:
        """Update a ClusterRole."""
        ...

    def delete_cluster_role(self, name: str) -> None:
        """Delete a ClusterRole."""
        ...

    # RoleBinding operations
    def get_role_binding(self, name: str, namespace: str) -> Any:
        """Get a RoleBinding by name and namespace."""
        ...

    def role_binding_exists(self, name: str, namespace: str) -> bool:
        """Check if a RoleBinding exists."""
        ...

    def create_role_binding(
        self,
        name: str,
        namespace: str,
        role_ref: Any,
        subjects: List[Any],
        labels: Optional[Dict[str, str]] = None
    ) -> Any:
        """Create a RoleBinding."""
        ...

    def update_role_binding(
        self,
        name: str,
        namespace: str,
        role_ref: Any,
        subjects: List[Any]
    ) -> Any:
        """Update a RoleBinding."""
        ...

    def delete_role_binding(self, name: str, namespace: str) -> None:
        """Delete a RoleBinding."""
        ...

    def list_role_bindings(self, namespace: str) -> List[Any]:
        """List all RoleBindings in a namespace."""
        ...

    # ClusterRoleBinding operations
    def get_cluster_role_binding(self, name: str) -> Any:
        """Get a ClusterRoleBinding by name."""
        ...

    def cluster_role_binding_exists(self, name: str) -> bool:
        """Check if a ClusterRoleBinding exists."""
        ...

    def create_cluster_role_binding(
        self,
        name: str,
        role_ref: Any,
        subjects: List[Any],
        labels: Optional[Dict[str, str]] = None
    ) -> Any:
        """Create a ClusterRoleBinding."""
        ...

    def update_cluster_role_binding(
        self,
        name: str,
        role_ref: Any,
        subjects: List[Any]
    ) -> Any:
        """Update a ClusterRoleBinding."""
        ...

    def delete_cluster_role_binding(self, name: str) -> None:
        """Delete a ClusterRoleBinding."""
        ...

    def list_cluster_role_bindings(self) -> List[Any]:
        """List all ClusterRoleBindings."""
        ...

    # Helper methods
    def create_service_account_subject(self, name: str, namespace: str) -> Any:
        """Create a ServiceAccount subject for bindings."""
        ...

    def create_group_subject(self, name: str, namespace: Optional[str] = None) -> Any:
        """Create a Group subject for bindings."""
        ...

    def create_user_subject(self, name: str) -> Any:
        """Create a User subject for bindings."""
        ...

    def create_cluster_role_ref(self, name: str) -> Any:
        """Create a ClusterRole role reference."""
        ...

    def create_role_ref(self, name: str) -> Any:
        """Create a Role role reference."""
        ...


@runtime_checkable
class IUserService(Protocol):
    """Protocol for user management service."""

    def create_user(
        self,
        name: str,
        namespace: str,
        role_ref: str,
        namespaces: List[str],
        generate_kubeconfig: bool = True
    ) -> Dict[str, Any]:
        """Create a user with all associated resources."""
        ...

    def update_user(
        self,
        name: str,
        namespace: str,
        role_ref: str,
        namespaces: List[str]
    ) -> Dict[str, Any]:
        """Update a user's configuration."""
        ...

    def delete_user(self, name: str, namespace: str) -> None:
        """Delete a user and all associated resources."""
        ...


@runtime_checkable
class IGroupService(Protocol):
    """Protocol for group management service."""

    def create_group(
        self,
        name: str,
        role_ref: str,
        namespaces: List[str],
        members: List[str]
    ) -> Dict[str, Any]:
        """Create a group with role bindings."""
        ...

    def update_group(
        self,
        name: str,
        role_ref: str,
        namespaces: List[str],
        members: List[str]
    ) -> Dict[str, Any]:
        """Update a group's configuration."""
        ...

    def delete_group(self, name: str) -> None:
        """Delete a group and its bindings."""
        ...


@runtime_checkable
class IRoleService(Protocol):
    """Protocol for role management service."""

    def create_role(
        self,
        name: str,
        rules: List[Dict[str, Any]],
        cluster_role: bool = False,
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a role with the specified rules."""
        ...

    def update_role(
        self,
        name: str,
        rules: List[Dict[str, Any]],
        cluster_role: bool = False,
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a role's rules."""
        ...

    def delete_role(
        self,
        name: str,
        cluster_role: bool = False,
        namespace: Optional[str] = None
    ) -> None:
        """Delete a role."""
        ...


@runtime_checkable
class IKubeconfigService(Protocol):
    """Protocol for kubeconfig generation service."""

    def generate_kubeconfig(
        self,
        user_name: str,
        namespace: str,
        service_account_name: str
    ) -> str:
        """Generate a kubeconfig for a user."""
        ...

    def get_cluster_info(self) -> Dict[str, str]:
        """Get cluster endpoint and CA information."""
        ...
