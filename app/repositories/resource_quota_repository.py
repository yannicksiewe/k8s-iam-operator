"""Repository for Kubernetes ResourceQuota operations."""

import logging
from typing import Optional, Dict

from kubernetes import client
from kubernetes.client.rest import ApiException

from app.repositories.base import BaseRepository
from app.exceptions import KubernetesAPIError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class ResourceQuotaRepository(BaseRepository):
    """Repository for managing Kubernetes ResourceQuota resources."""

    def __init__(self, core_api: Optional[client.CoreV1Api] = None):
        """Initialize the repository.

        Args:
            core_api: Optional Kubernetes CoreV1Api client
        """
        super().__init__()
        self.core_api = core_api or client.CoreV1Api()

    def get(self, name: str, namespace: str) -> client.V1ResourceQuota:
        """Get a ResourceQuota by name.

        Args:
            name: The ResourceQuota name
            namespace: The namespace

        Returns:
            The ResourceQuota object

        Raises:
            ResourceNotFoundError: If not found
            KubernetesAPIError: If API call fails
        """
        try:
            return self.core_api.read_namespaced_resource_quota(name, namespace)
        except ApiException as e:
            if e.status == 404:
                raise ResourceNotFoundError("ResourceQuota", name, namespace)
            raise KubernetesAPIError(
                "get_resource_quota",
                f"Failed to get ResourceQuota '{name}': {e.reason}",
                e.status
            )

    def exists(self, name: str, namespace: str) -> bool:
        """Check if a ResourceQuota exists.

        Args:
            name: The ResourceQuota name
            namespace: The namespace

        Returns:
            True if exists, False otherwise
        """
        try:
            self.get(name, namespace)
            return True
        except ResourceNotFoundError:
            return False

    def create(
        self,
        name: str,
        namespace: str,
        hard: Dict[str, str],
        labels: Optional[Dict[str, str]] = None
    ) -> client.V1ResourceQuota:
        """Create a ResourceQuota.

        Args:
            name: The ResourceQuota name
            namespace: The namespace
            hard: The hard limits dict (e.g., {"cpu": "4", "memory": "8Gi"})
            labels: Optional labels

        Returns:
            The created ResourceQuota

        Raises:
            KubernetesAPIError: If creation fails
        """
        quota = client.V1ResourceQuota(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=labels or {}
            ),
            spec=client.V1ResourceQuotaSpec(
                hard=hard
            )
        )

        try:
            result = self.core_api.create_namespaced_resource_quota(namespace, quota)
            logger.info(f"Created ResourceQuota '{name}' in namespace '{namespace}'")
            return result
        except ApiException as e:
            raise KubernetesAPIError(
                "create_resource_quota",
                f"Failed to create ResourceQuota '{name}': {e.reason}",
                e.status
            )

    def update(
        self,
        name: str,
        namespace: str,
        hard: Dict[str, str]
    ) -> client.V1ResourceQuota:
        """Update a ResourceQuota.

        Args:
            name: The ResourceQuota name
            namespace: The namespace
            hard: The new hard limits

        Returns:
            The updated ResourceQuota

        Raises:
            ResourceNotFoundError: If not found
            KubernetesAPIError: If update fails
        """
        try:
            existing = self.get(name, namespace)
            existing.spec.hard = hard
            result = self.core_api.replace_namespaced_resource_quota(
                name, namespace, existing
            )
            logger.info(f"Updated ResourceQuota '{name}' in namespace '{namespace}'")
            return result
        except ApiException as e:
            raise KubernetesAPIError(
                "update_resource_quota",
                f"Failed to update ResourceQuota '{name}': {e.reason}",
                e.status
            )

    def delete(self, name: str, namespace: str) -> None:
        """Delete a ResourceQuota.

        Args:
            name: The ResourceQuota name
            namespace: The namespace

        Raises:
            ResourceNotFoundError: If not found
            KubernetesAPIError: If deletion fails
        """
        try:
            self.core_api.delete_namespaced_resource_quota(name, namespace)
            logger.info(f"Deleted ResourceQuota '{name}' from namespace '{namespace}'")
        except ApiException as e:
            if e.status == 404:
                raise ResourceNotFoundError("ResourceQuota", name, namespace)
            raise KubernetesAPIError(
                "delete_resource_quota",
                f"Failed to delete ResourceQuota '{name}': {e.reason}",
                e.status
            )

    def ensure_exists(
        self,
        name: str,
        namespace: str,
        hard: Dict[str, str],
        labels: Optional[Dict[str, str]] = None
    ) -> client.V1ResourceQuota:
        """Ensure a ResourceQuota exists, creating or updating as needed.

        Args:
            name: The ResourceQuota name
            namespace: The namespace
            hard: The hard limits
            labels: Optional labels

        Returns:
            The ResourceQuota object
        """
        if self.exists(name, namespace):
            return self.update(name, namespace, hard)
        return self.create(name, namespace, hard, labels)
