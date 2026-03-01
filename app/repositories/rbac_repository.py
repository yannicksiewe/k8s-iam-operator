"""RBAC repository for Kubernetes RBAC operations."""

from typing import List, Optional

from kubernetes import client
from kubernetes.client.rest import ApiException

from app.repositories.base import BaseRepository
from app.exceptions import ResourceNotFoundError, ResourceAlreadyExistsError


class RBACRepository(BaseRepository):
    """Repository for Kubernetes RBAC operations (Roles, ClusterRoles, Bindings)."""

    def __init__(self, api_client: Optional[client.ApiClient] = None):
        super().__init__(api_client)
        self._rbac_v1 = client.RbacAuthorizationV1Api(self.api_client)

    # ==================== Role Operations ====================

    def get_role(self, name: str, namespace: str) -> client.V1Role:
        """Get a Role by name and namespace.

        Args:
            name: The role name
            namespace: The namespace

        Returns:
            The V1Role object

        Raises:
            ResourceNotFoundError: If role doesn't exist
            KubernetesAPIError: For other API errors
        """
        try:
            return self._rbac_v1.read_namespaced_role(name=name, namespace=namespace)
        except ApiException as e:
            self.handle_api_exception(e, "get", "Role", name, namespace)

    def role_exists(self, name: str, namespace: str) -> bool:
        """Check if a role exists."""
        try:
            self._rbac_v1.read_namespaced_role(name=name, namespace=namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def create_role(self, name: str, namespace: str,
                    rules: List[dict],
                    labels: Optional[dict] = None) -> client.V1Role:
        """Create a Role.

        Args:
            name: The role name
            namespace: The namespace
            rules: List of policy rules
            labels: Optional labels

        Returns:
            The created V1Role object
        """
        metadata = client.V1ObjectMeta(name=name, labels=labels or {})
        role = client.V1Role(metadata=metadata, rules=rules)

        try:
            return self._rbac_v1.create_namespaced_role(namespace=namespace, body=role)
        except ApiException as e:
            self.handle_api_exception(e, "create", "Role", name, namespace)

    def update_role(self, name: str, namespace: str,
                    rules: List[dict]) -> client.V1Role:
        """Update a Role.

        Args:
            name: The role name
            namespace: The namespace
            rules: New list of policy rules

        Returns:
            The updated V1Role object
        """
        body = client.V1Role(
            metadata=client.V1ObjectMeta(name=name),
            rules=rules
        )
        try:
            return self._rbac_v1.patch_namespaced_role(
                name=name, namespace=namespace, body=body
            )
        except ApiException as e:
            self.handle_api_exception(e, "update", "Role", name, namespace)

    def delete_role(self, name: str, namespace: str) -> None:
        """Delete a Role."""
        try:
            self._rbac_v1.delete_namespaced_role(name=name, namespace=namespace)
        except ApiException as e:
            self.handle_api_exception(e, "delete", "Role", name, namespace)

    # ==================== ClusterRole Operations ====================

    def get_cluster_role(self, name: str) -> client.V1ClusterRole:
        """Get a ClusterRole by name."""
        try:
            return self._rbac_v1.read_cluster_role(name=name)
        except ApiException as e:
            self.handle_api_exception(e, "get", "ClusterRole", name)

    def cluster_role_exists(self, name: str) -> bool:
        """Check if a ClusterRole exists."""
        try:
            self._rbac_v1.read_cluster_role(name=name)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def create_cluster_role(self, name: str, rules: List[dict],
                            labels: Optional[dict] = None) -> client.V1ClusterRole:
        """Create a ClusterRole."""
        metadata = client.V1ObjectMeta(name=name, labels=labels or {})
        role = client.V1ClusterRole(metadata=metadata, rules=rules)

        try:
            return self._rbac_v1.create_cluster_role(body=role)
        except ApiException as e:
            self.handle_api_exception(e, "create", "ClusterRole", name)

    def update_cluster_role(self, name: str, rules: List[dict]) -> client.V1ClusterRole:
        """Update a ClusterRole."""
        body = client.V1ClusterRole(
            metadata=client.V1ObjectMeta(name=name),
            rules=rules
        )
        try:
            return self._rbac_v1.patch_cluster_role(name=name, body=body)
        except ApiException as e:
            self.handle_api_exception(e, "update", "ClusterRole", name)

    def delete_cluster_role(self, name: str) -> None:
        """Delete a ClusterRole."""
        try:
            self._rbac_v1.delete_cluster_role(name=name)
        except ApiException as e:
            self.handle_api_exception(e, "delete", "ClusterRole", name)

    def create_or_update_cluster_role(self, name: str, rules: List[dict],
                                       labels: Optional[dict] = None) -> client.V1ClusterRole:
        """Create or update a ClusterRole."""
        try:
            return self.create_cluster_role(name, rules, labels)
        except ResourceAlreadyExistsError:
            return self.update_cluster_role(name, rules)

    # ==================== RoleBinding Operations ====================

    def get_role_binding(self, name: str, namespace: str) -> client.V1RoleBinding:
        """Get a RoleBinding by name and namespace."""
        try:
            return self._rbac_v1.read_namespaced_role_binding(
                name=name, namespace=namespace
            )
        except ApiException as e:
            self.handle_api_exception(e, "get", "RoleBinding", name, namespace)

    def role_binding_exists(self, name: str, namespace: str) -> bool:
        """Check if a RoleBinding exists."""
        try:
            self._rbac_v1.read_namespaced_role_binding(name=name, namespace=namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def create_role_binding(self, name: str, namespace: str,
                            role_ref: client.V1RoleRef,
                            subjects: List[client.V1Subject],
                            labels: Optional[dict] = None) -> client.V1RoleBinding:
        """Create a RoleBinding."""
        metadata = client.V1ObjectMeta(name=name, namespace=namespace, labels=labels or {})
        binding = client.V1RoleBinding(
            metadata=metadata,
            role_ref=role_ref,
            subjects=subjects
        )

        try:
            return self._rbac_v1.create_namespaced_role_binding(
                namespace=namespace, body=binding
            )
        except ApiException as e:
            self.handle_api_exception(e, "create", "RoleBinding", name, namespace)

    def update_role_binding(self, name: str, namespace: str,
                            role_ref: client.V1RoleRef,
                            subjects: List[client.V1Subject]) -> client.V1RoleBinding:
        """Update a RoleBinding."""
        binding = client.V1RoleBinding(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            role_ref=role_ref,
            subjects=subjects
        )
        try:
            return self._rbac_v1.patch_namespaced_role_binding(
                name=name, namespace=namespace, body=binding
            )
        except ApiException as e:
            self.handle_api_exception(e, "update", "RoleBinding", name, namespace)

    def delete_role_binding(self, name: str, namespace: str) -> None:
        """Delete a RoleBinding."""
        try:
            self._rbac_v1.delete_namespaced_role_binding(name=name, namespace=namespace)
        except ApiException as e:
            self.handle_api_exception(e, "delete", "RoleBinding", name, namespace)

    def list_role_bindings(self, namespace: str) -> List[client.V1RoleBinding]:
        """List all RoleBindings in a namespace."""
        result = self._rbac_v1.list_namespaced_role_binding(namespace=namespace)
        return result.items

    def create_or_update_role_binding(self, name: str, namespace: str,
                                       role_ref: client.V1RoleRef,
                                       subjects: List[client.V1Subject],
                                       labels: Optional[dict] = None) -> client.V1RoleBinding:
        """Create or update a RoleBinding."""
        try:
            return self.create_role_binding(name, namespace, role_ref, subjects, labels)
        except ResourceAlreadyExistsError:
            return self.update_role_binding(name, namespace, role_ref, subjects)

    # ==================== ClusterRoleBinding Operations ====================

    def get_cluster_role_binding(self, name: str) -> client.V1ClusterRoleBinding:
        """Get a ClusterRoleBinding by name."""
        try:
            return self._rbac_v1.read_cluster_role_binding(name=name)
        except ApiException as e:
            self.handle_api_exception(e, "get", "ClusterRoleBinding", name)

    def cluster_role_binding_exists(self, name: str) -> bool:
        """Check if a ClusterRoleBinding exists."""
        try:
            self._rbac_v1.read_cluster_role_binding(name=name)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def create_cluster_role_binding(self, name: str,
                                     role_ref: client.V1RoleRef,
                                     subjects: List[client.V1Subject],
                                     labels: Optional[dict] = None) -> client.V1ClusterRoleBinding:
        """Create a ClusterRoleBinding."""
        metadata = client.V1ObjectMeta(name=name, labels=labels or {})
        binding = client.V1ClusterRoleBinding(
            metadata=metadata,
            role_ref=role_ref,
            subjects=subjects
        )

        try:
            return self._rbac_v1.create_cluster_role_binding(body=binding)
        except ApiException as e:
            self.handle_api_exception(e, "create", "ClusterRoleBinding", name)

    def update_cluster_role_binding(self, name: str,
                                     role_ref: client.V1RoleRef,
                                     subjects: List[client.V1Subject]) -> client.V1ClusterRoleBinding:
        """Update a ClusterRoleBinding."""
        binding = client.V1ClusterRoleBinding(
            metadata=client.V1ObjectMeta(name=name),
            role_ref=role_ref,
            subjects=subjects
        )
        try:
            return self._rbac_v1.replace_cluster_role_binding(name=name, body=binding)
        except ApiException as e:
            self.handle_api_exception(e, "update", "ClusterRoleBinding", name)

    def delete_cluster_role_binding(self, name: str) -> None:
        """Delete a ClusterRoleBinding."""
        try:
            self._rbac_v1.delete_cluster_role_binding(name=name)
        except ApiException as e:
            self.handle_api_exception(e, "delete", "ClusterRoleBinding", name)

    def list_cluster_role_bindings(self) -> List[client.V1ClusterRoleBinding]:
        """List all ClusterRoleBindings."""
        result = self._rbac_v1.list_cluster_role_binding()
        return result.items

    def create_or_update_cluster_role_binding(
        self, name: str,
        role_ref: client.V1RoleRef,
        subjects: List[client.V1Subject],
        labels: Optional[dict] = None
    ) -> client.V1ClusterRoleBinding:
        """Create or update a ClusterRoleBinding."""
        try:
            return self.create_cluster_role_binding(name, role_ref, subjects, labels)
        except ResourceAlreadyExistsError:
            return self.update_cluster_role_binding(name, role_ref, subjects)

    # ==================== Helper Methods ====================

    def create_service_account_subject(self, name: str, namespace: str) -> client.V1Subject:
        """Create a ServiceAccount subject for bindings."""
        return client.V1Subject(
            api_group="",
            kind="ServiceAccount",
            name=name,
            namespace=namespace
        )

    def create_group_subject(self, name: str,
                              namespace: Optional[str] = None) -> client.V1Subject:
        """Create a Group subject for bindings."""
        return client.V1Subject(
            api_group="rbac.authorization.k8s.io",
            kind="Group",
            name=name,
            namespace=namespace
        )

    def create_user_subject(self, name: str) -> client.V1Subject:
        """Create a User subject for bindings."""
        return client.V1Subject(
            api_group="rbac.authorization.k8s.io",
            kind="User",
            name=name
        )

    def create_cluster_role_ref(self, name: str) -> client.V1RoleRef:
        """Create a ClusterRole role reference."""
        return client.V1RoleRef(
            api_group="rbac.authorization.k8s.io",
            kind="ClusterRole",
            name=name
        )

    def create_role_ref(self, name: str) -> client.V1RoleRef:
        """Create a Role role reference."""
        return client.V1RoleRef(
            api_group="rbac.authorization.k8s.io",
            kind="Role",
            name=name
        )

    def find_bindings_for_subject(self, subject_name: str, subject_kind: str,
                                   namespace: Optional[str] = None) -> List[client.V1RoleBinding]:
        """Find all RoleBindings for a given subject across namespaces.

        Args:
            subject_name: Name of the subject
            subject_kind: Kind of subject (ServiceAccount, Group, User)
            namespace: If provided, only search this namespace

        Returns:
            List of matching RoleBindings
        """
        matching = []

        if namespace:
            bindings = self.list_role_bindings(namespace)
            for binding in bindings:
                if binding.subjects:
                    for subject in binding.subjects:
                        if subject.name == subject_name and subject.kind == subject_kind:
                            matching.append(binding)
                            break
        else:
            # List from all namespaces
            core_v1 = client.CoreV1Api(self.api_client)
            namespaces = core_v1.list_namespace().items
            for ns in namespaces:
                bindings = self.list_role_bindings(ns.metadata.name)
                for binding in bindings:
                    if binding.subjects:
                        for subject in binding.subjects:
                            if subject.name == subject_name and subject.kind == subject_kind:
                                matching.append(binding)
                                break

        return matching

    def find_cluster_role_bindings_for_subject(
        self, subject_name: str, subject_kind: str
    ) -> List[client.V1ClusterRoleBinding]:
        """Find all ClusterRoleBindings for a given subject.

        Args:
            subject_name: Name of the subject
            subject_kind: Kind of subject (ServiceAccount, Group, User)

        Returns:
            List of matching ClusterRoleBindings
        """
        matching = []
        bindings = self.list_cluster_role_bindings()

        for binding in bindings:
            if binding.subjects:
                for subject in binding.subjects:
                    if subject.name == subject_name and subject.kind == subject_kind:
                        matching.append(binding)
                        break

        return matching
