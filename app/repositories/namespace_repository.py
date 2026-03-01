"""Namespace repository for Kubernetes namespace operations."""

from typing import List, Optional

from kubernetes import client
from kubernetes.client.rest import ApiException

from app.repositories.base import BaseRepository
from app.exceptions import ResourceNotFoundError, ResourceAlreadyExistsError


class NamespaceRepository(BaseRepository):
    """Repository for Kubernetes Namespace operations."""

    def __init__(self, api_client: Optional[client.ApiClient] = None):
        super().__init__(api_client)
        self._core_v1 = client.CoreV1Api(self.api_client)

    def get(self, name: str) -> client.V1Namespace:
        """Get a namespace by name.

        Args:
            name: The namespace name

        Returns:
            The V1Namespace object

        Raises:
            ResourceNotFoundError: If namespace doesn't exist
            KubernetesAPIError: For other API errors
        """
        try:
            return self._core_v1.read_namespace(name=name)
        except ApiException as e:
            self.handle_api_exception(e, "get", "Namespace", name)

    def exists(self, name: str) -> bool:
        """Check if a namespace exists.

        Args:
            name: The namespace name

        Returns:
            True if namespace exists, False otherwise
        """
        try:
            self._core_v1.read_namespace(name=name)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def create(self, name: str, labels: Optional[dict] = None,
               annotations: Optional[dict] = None) -> client.V1Namespace:
        """Create a namespace.

        Args:
            name: The namespace name
            labels: Optional labels to apply
            annotations: Optional annotations to apply

        Returns:
            The created V1Namespace object

        Raises:
            ResourceAlreadyExistsError: If namespace already exists
            KubernetesAPIError: For other API errors
        """
        metadata = client.V1ObjectMeta(
            name=name,
            labels=labels or {},
            annotations=annotations or {}
        )
        namespace = client.V1Namespace(metadata=metadata)

        try:
            return self._core_v1.create_namespace(body=namespace)
        except ApiException as e:
            self.handle_api_exception(e, "create", "Namespace", name)

    def delete(self, name: str, grace_period_seconds: int = 0) -> None:
        """Delete a namespace.

        Args:
            name: The namespace name
            grace_period_seconds: Grace period for deletion

        Raises:
            ResourceNotFoundError: If namespace doesn't exist
            KubernetesAPIError: For other API errors
        """
        delete_options = client.V1DeleteOptions(
            propagation_policy='Foreground',
            grace_period_seconds=grace_period_seconds
        )
        try:
            self._core_v1.delete_namespace(name=name, body=delete_options)
        except ApiException as e:
            self.handle_api_exception(e, "delete", "Namespace", name)

    def list_all(self) -> List[client.V1Namespace]:
        """List all namespaces.

        Returns:
            List of V1Namespace objects
        """
        result = self._core_v1.list_namespace()
        return result.items

    def list_names(self) -> List[str]:
        """List all namespace names.

        Returns:
            List of namespace names
        """
        namespaces = self.list_all()
        return [ns.metadata.name for ns in namespaces]

    def ensure_exists(self, name: str, labels: Optional[dict] = None,
                      annotations: Optional[dict] = None) -> client.V1Namespace:
        """Ensure a namespace exists, creating it if necessary.

        Args:
            name: The namespace name
            labels: Optional labels to apply (only on create)
            annotations: Optional annotations to apply (only on create)

        Returns:
            The V1Namespace object (existing or newly created)
        """
        try:
            return self.get(name)
        except ResourceNotFoundError:
            return self.create(name, labels=labels, annotations=annotations)
