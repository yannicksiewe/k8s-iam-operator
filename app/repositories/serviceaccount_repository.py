"""ServiceAccount repository for Kubernetes service account operations."""

from typing import List, Optional

from kubernetes import client
from kubernetes.client.rest import ApiException

from app.repositories.base import BaseRepository
from app.exceptions import ResourceNotFoundError


class ServiceAccountRepository(BaseRepository):
    """Repository for Kubernetes ServiceAccount operations."""

    def __init__(self, api_client: Optional[client.ApiClient] = None):
        super().__init__(api_client)
        self._core_v1 = client.CoreV1Api(self.api_client)

    def get(self, name: str, namespace: str) -> client.V1ServiceAccount:
        """Get a service account by name and namespace.

        Args:
            name: The service account name
            namespace: The namespace

        Returns:
            The V1ServiceAccount object

        Raises:
            ResourceNotFoundError: If service account doesn't exist
            KubernetesAPIError: For other API errors
        """
        try:
            return self._core_v1.read_namespaced_service_account(
                name=name, namespace=namespace
            )
        except ApiException as e:
            self.handle_api_exception(e, "get", "ServiceAccount", name, namespace)

    def exists(self, name: str, namespace: str) -> bool:
        """Check if a service account exists.

        Args:
            name: The service account name
            namespace: The namespace

        Returns:
            True if service account exists, False otherwise
        """
        try:
            self._core_v1.read_namespaced_service_account(name=name, namespace=namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def create(self, name: str, namespace: str,
               labels: Optional[dict] = None,
               annotations: Optional[dict] = None,
               automount_token: bool = True) -> client.V1ServiceAccount:
        """Create a service account.

        Args:
            name: The service account name
            namespace: The namespace
            labels: Optional labels to apply
            annotations: Optional annotations to apply
            automount_token: Whether to automount the service account token

        Returns:
            The created V1ServiceAccount object

        Raises:
            ResourceAlreadyExistsError: If service account already exists
            KubernetesAPIError: For other API errors
        """
        metadata = client.V1ObjectMeta(
            name=name,
            labels=labels or {},
            annotations=annotations or {}
        )
        sa = client.V1ServiceAccount(
            metadata=metadata,
            automount_service_account_token=automount_token
        )

        try:
            return self._core_v1.create_namespaced_service_account(
                namespace=namespace, body=sa
            )
        except ApiException as e:
            self.handle_api_exception(e, "create", "ServiceAccount", name, namespace)

    def update(self, name: str, namespace: str,
               labels: Optional[dict] = None,
               annotations: Optional[dict] = None) -> client.V1ServiceAccount:
        """Update a service account.

        Args:
            name: The service account name
            namespace: The namespace
            labels: Optional labels to update
            annotations: Optional annotations to update

        Returns:
            The updated V1ServiceAccount object

        Raises:
            ResourceNotFoundError: If service account doesn't exist
            KubernetesAPIError: For other API errors
        """
        patch_body = {}
        if labels is not None or annotations is not None:
            patch_body["metadata"] = {}
            if labels is not None:
                patch_body["metadata"]["labels"] = labels
            if annotations is not None:
                patch_body["metadata"]["annotations"] = annotations

        try:
            return self._core_v1.patch_namespaced_service_account(
                name=name, namespace=namespace, body=patch_body
            )
        except ApiException as e:
            self.handle_api_exception(e, "update", "ServiceAccount", name, namespace)

    def delete(self, name: str, namespace: str,
               grace_period_seconds: int = 5) -> None:
        """Delete a service account.

        Args:
            name: The service account name
            namespace: The namespace
            grace_period_seconds: Grace period for deletion

        Raises:
            ResourceNotFoundError: If service account doesn't exist
            KubernetesAPIError: For other API errors
        """
        delete_options = client.V1DeleteOptions(
            propagation_policy='Foreground',
            grace_period_seconds=grace_period_seconds
        )
        try:
            self._core_v1.delete_namespaced_service_account(
                name=name, namespace=namespace, body=delete_options
            )
        except ApiException as e:
            self.handle_api_exception(e, "delete", "ServiceAccount", name, namespace)

    def list_in_namespace(self, namespace: str) -> List[client.V1ServiceAccount]:
        """List all service accounts in a namespace.

        Args:
            namespace: The namespace

        Returns:
            List of V1ServiceAccount objects
        """
        result = self._core_v1.list_namespaced_service_account(namespace=namespace)
        return result.items

    def ensure_exists(self, name: str, namespace: str,
                      labels: Optional[dict] = None,
                      annotations: Optional[dict] = None,
                      automount_token: bool = True) -> client.V1ServiceAccount:
        """Ensure a service account exists, creating it if necessary.

        Args:
            name: The service account name
            namespace: The namespace
            labels: Optional labels to apply (only on create)
            annotations: Optional annotations to apply (only on create)
            automount_token: Whether to automount the service account token

        Returns:
            The V1ServiceAccount object (existing or newly created)
        """
        try:
            return self.get(name, namespace)
        except ResourceNotFoundError:
            return self.create(
                name, namespace,
                labels=labels,
                annotations=annotations,
                automount_token=automount_token
            )
