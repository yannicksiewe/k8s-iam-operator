"""Repository for Kubernetes NetworkPolicy operations."""

import logging
from typing import Optional, Dict, List

from kubernetes import client
from kubernetes.client.rest import ApiException

from app.repositories.base import BaseRepository
from app.exceptions import KubernetesAPIError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class NetworkPolicyRepository(BaseRepository):
    """Repository for managing Kubernetes NetworkPolicy resources."""

    def __init__(self, networking_api: Optional[client.NetworkingV1Api] = None):
        """Initialize the repository.

        Args:
            networking_api: Optional Kubernetes NetworkingV1Api client
        """
        super().__init__()
        self.networking_api = networking_api or client.NetworkingV1Api()

    def get(self, name: str, namespace: str) -> client.V1NetworkPolicy:
        """Get a NetworkPolicy by name.

        Args:
            name: The NetworkPolicy name
            namespace: The namespace

        Returns:
            The NetworkPolicy object

        Raises:
            ResourceNotFoundError: If not found
            KubernetesAPIError: If API call fails
        """
        try:
            return self.networking_api.read_namespaced_network_policy(name, namespace)
        except ApiException as e:
            if e.status == 404:
                raise ResourceNotFoundError("NetworkPolicy", name, namespace)
            raise KubernetesAPIError(
                "get_network_policy",
                f"Failed to get NetworkPolicy '{name}': {e.reason}",
                e.status
            )

    def exists(self, name: str, namespace: str) -> bool:
        """Check if a NetworkPolicy exists.

        Args:
            name: The NetworkPolicy name
            namespace: The namespace

        Returns:
            True if exists, False otherwise
        """
        try:
            self.get(name, namespace)
            return True
        except ResourceNotFoundError:
            return False

    def create_isolated_policy(
        self,
        name: str,
        namespace: str,
        labels: Optional[Dict[str, str]] = None
    ) -> client.V1NetworkPolicy:
        """Create an isolated NetworkPolicy (deny all ingress except same namespace).

        Args:
            name: The NetworkPolicy name
            namespace: The namespace
            labels: Optional labels

        Returns:
            The created NetworkPolicy
        """
        policy = client.V1NetworkPolicy(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=labels or {}
            ),
            spec=client.V1NetworkPolicySpec(
                pod_selector=client.V1LabelSelector(),  # Select all pods
                policy_types=["Ingress"],
                ingress=[
                    client.V1NetworkPolicyIngressRule(
                        _from=[
                            client.V1NetworkPolicyPeer(
                                namespace_selector=client.V1LabelSelector(
                                    match_labels={
                                        "kubernetes.io/metadata.name": namespace
                                    }
                                )
                            )
                        ]
                    )
                ]
            )
        )
        return self._create(policy, namespace)

    def create_restricted_policy(
        self,
        name: str,
        namespace: str,
        labels: Optional[Dict[str, str]] = None
    ) -> client.V1NetworkPolicy:
        """Create a restricted NetworkPolicy (deny all except DNS and same namespace).

        Args:
            name: The NetworkPolicy name
            namespace: The namespace
            labels: Optional labels

        Returns:
            The created NetworkPolicy
        """
        policy = client.V1NetworkPolicy(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels=labels or {}
            ),
            spec=client.V1NetworkPolicySpec(
                pod_selector=client.V1LabelSelector(),  # Select all pods
                policy_types=["Ingress", "Egress"],
                ingress=[
                    # Allow from same namespace
                    client.V1NetworkPolicyIngressRule(
                        _from=[
                            client.V1NetworkPolicyPeer(
                                namespace_selector=client.V1LabelSelector(
                                    match_labels={
                                        "kubernetes.io/metadata.name": namespace
                                    }
                                )
                            )
                        ]
                    )
                ],
                egress=[
                    # Allow DNS (kube-system)
                    client.V1NetworkPolicyEgressRule(
                        to=[
                            client.V1NetworkPolicyPeer(
                                namespace_selector=client.V1LabelSelector(
                                    match_labels={
                                        "kubernetes.io/metadata.name": "kube-system"
                                    }
                                )
                            )
                        ],
                        ports=[
                            client.V1NetworkPolicyPort(
                                port=53,
                                protocol="UDP"
                            ),
                            client.V1NetworkPolicyPort(
                                port=53,
                                protocol="TCP"
                            )
                        ]
                    ),
                    # Allow to same namespace
                    client.V1NetworkPolicyEgressRule(
                        to=[
                            client.V1NetworkPolicyPeer(
                                namespace_selector=client.V1LabelSelector(
                                    match_labels={
                                        "kubernetes.io/metadata.name": namespace
                                    }
                                )
                            )
                        ]
                    )
                ]
            )
        )
        return self._create(policy, namespace)

    def _create(
        self,
        policy: client.V1NetworkPolicy,
        namespace: str
    ) -> client.V1NetworkPolicy:
        """Create a NetworkPolicy.

        Args:
            policy: The NetworkPolicy object
            namespace: The namespace

        Returns:
            The created NetworkPolicy

        Raises:
            KubernetesAPIError: If creation fails
        """
        try:
            result = self.networking_api.create_namespaced_network_policy(
                namespace, policy
            )
            logger.info(
                f"Created NetworkPolicy '{policy.metadata.name}' "
                f"in namespace '{namespace}'"
            )
            return result
        except ApiException as e:
            raise KubernetesAPIError(
                "create_network_policy",
                f"Failed to create NetworkPolicy '{policy.metadata.name}': {e.reason}",
                e.status
            )

    def delete(self, name: str, namespace: str) -> None:
        """Delete a NetworkPolicy.

        Args:
            name: The NetworkPolicy name
            namespace: The namespace

        Raises:
            ResourceNotFoundError: If not found
            KubernetesAPIError: If deletion fails
        """
        try:
            self.networking_api.delete_namespaced_network_policy(name, namespace)
            logger.info(f"Deleted NetworkPolicy '{name}' from namespace '{namespace}'")
        except ApiException as e:
            if e.status == 404:
                raise ResourceNotFoundError("NetworkPolicy", name, namespace)
            raise KubernetesAPIError(
                "delete_network_policy",
                f"Failed to delete NetworkPolicy '{name}': {e.reason}",
                e.status
            )

    def delete_if_exists(self, name: str, namespace: str) -> bool:
        """Delete a NetworkPolicy if it exists.

        Args:
            name: The NetworkPolicy name
            namespace: The namespace

        Returns:
            True if deleted, False if didn't exist
        """
        try:
            self.delete(name, namespace)
            return True
        except ResourceNotFoundError:
            return False
