"""Secret repository for Kubernetes secret operations."""

from typing import Dict, List, Optional

from kubernetes import client
from kubernetes.client.rest import ApiException

from app.repositories.base import BaseRepository
from app.exceptions import ResourceNotFoundError, ResourceAlreadyExistsError


class SecretRepository(BaseRepository):
    """Repository for Kubernetes Secret operations."""

    def __init__(self, api_client: Optional[client.ApiClient] = None):
        super().__init__(api_client)
        self._core_v1 = client.CoreV1Api(self.api_client)

    def get(self, name: str, namespace: str) -> client.V1Secret:
        """Get a secret by name and namespace.

        Args:
            name: The secret name
            namespace: The namespace

        Returns:
            The V1Secret object

        Raises:
            ResourceNotFoundError: If secret doesn't exist
            KubernetesAPIError: For other API errors
        """
        try:
            return self._core_v1.read_namespaced_secret(name=name, namespace=namespace)
        except ApiException as e:
            self.handle_api_exception(e, "get", "Secret", name, namespace)

    def exists(self, name: str, namespace: str) -> bool:
        """Check if a secret exists.

        Args:
            name: The secret name
            namespace: The namespace

        Returns:
            True if secret exists, False otherwise
        """
        try:
            self._core_v1.read_namespaced_secret(name=name, namespace=namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def create(self, name: str, namespace: str,
               data: Dict[str, str],
               secret_type: str = "Opaque",
               labels: Optional[dict] = None,
               annotations: Optional[dict] = None) -> client.V1Secret:
        """Create a secret.

        Args:
            name: The secret name
            namespace: The namespace
            data: Secret data (will be stored as-is, should be base64 encoded)
            secret_type: Type of secret (default: Opaque)
            labels: Optional labels to apply
            annotations: Optional annotations to apply

        Returns:
            The created V1Secret object

        Raises:
            ResourceAlreadyExistsError: If secret already exists
            KubernetesAPIError: For other API errors
        """
        metadata = client.V1ObjectMeta(
            name=name,
            labels=labels or {},
            annotations=annotations or {}
        )
        secret = client.V1Secret(
            metadata=metadata,
            type=secret_type,
            data=data
        )

        try:
            return self._core_v1.create_namespaced_secret(
                namespace=namespace, body=secret
            )
        except ApiException as e:
            self.handle_api_exception(e, "create", "Secret", name, namespace)

    def create_service_account_token(self, sa_name: str, namespace: str,
                                      token_name: Optional[str] = None) -> client.V1Secret:
        """Create a service account token secret.

        Args:
            sa_name: The service account name
            namespace: The namespace
            token_name: Optional custom name for the token secret

        Returns:
            The created V1Secret object

        Raises:
            ResourceAlreadyExistsError: If secret already exists
            KubernetesAPIError: For other API errors
        """
        name = token_name or f"{sa_name}-token"
        metadata = client.V1ObjectMeta(
            name=name,
            annotations={"kubernetes.io/service-account.name": sa_name}
        )
        secret = client.V1Secret(
            metadata=metadata,
            type="kubernetes.io/service-account-token"
        )

        try:
            return self._core_v1.create_namespaced_secret(
                namespace=namespace, body=secret
            )
        except ApiException as e:
            self.handle_api_exception(e, "create", "Secret", name, namespace)

    def create_kubeconfig_secret(self, name: str, namespace: str,
                                  kubeconfig_data: str) -> client.V1Secret:
        """Create a kubeconfig secret.

        Args:
            name: The secret name
            namespace: The namespace
            kubeconfig_data: Base64 encoded kubeconfig data

        Returns:
            The created V1Secret object

        Raises:
            ResourceAlreadyExistsError: If secret already exists
            KubernetesAPIError: For other API errors
        """
        return self.create(
            name=name,
            namespace=namespace,
            data={"kubeconfig": kubeconfig_data},
            secret_type="Opaque",
            labels={"k8s-iam-operator/type": "kubeconfig"}
        )

    def update(self, name: str, namespace: str,
               data: Optional[Dict[str, str]] = None,
               labels: Optional[dict] = None,
               annotations: Optional[dict] = None) -> client.V1Secret:
        """Update a secret.

        Args:
            name: The secret name
            namespace: The namespace
            data: Optional new data
            labels: Optional labels to update
            annotations: Optional annotations to update

        Returns:
            The updated V1Secret object

        Raises:
            ResourceNotFoundError: If secret doesn't exist
            KubernetesAPIError: For other API errors
        """
        patch_body = {}
        if data is not None:
            patch_body["data"] = data
        if labels is not None or annotations is not None:
            patch_body["metadata"] = {}
            if labels is not None:
                patch_body["metadata"]["labels"] = labels
            if annotations is not None:
                patch_body["metadata"]["annotations"] = annotations

        try:
            return self._core_v1.patch_namespaced_secret(
                name=name, namespace=namespace, body=patch_body
            )
        except ApiException as e:
            self.handle_api_exception(e, "update", "Secret", name, namespace)

    def delete(self, name: str, namespace: str) -> None:
        """Delete a secret.

        Args:
            name: The secret name
            namespace: The namespace

        Raises:
            ResourceNotFoundError: If secret doesn't exist
            KubernetesAPIError: For other API errors
        """
        try:
            self._core_v1.delete_namespaced_secret(name=name, namespace=namespace)
        except ApiException as e:
            self.handle_api_exception(e, "delete", "Secret", name, namespace)

    def list_in_namespace(self, namespace: str,
                          label_selector: Optional[str] = None) -> List[client.V1Secret]:
        """List secrets in a namespace.

        Args:
            namespace: The namespace
            label_selector: Optional label selector string

        Returns:
            List of V1Secret objects
        """
        result = self._core_v1.list_namespaced_secret(
            namespace=namespace,
            label_selector=label_selector
        )
        return result.items

    def get_configmap(self, name: str, namespace: str) -> client.V1ConfigMap:
        """Get a ConfigMap by name and namespace.

        Args:
            name: The ConfigMap name
            namespace: The namespace

        Returns:
            The V1ConfigMap object

        Raises:
            ResourceNotFoundError: If ConfigMap doesn't exist
            KubernetesAPIError: For other API errors
        """
        try:
            return self._core_v1.read_namespaced_config_map(
                name=name, namespace=namespace
            )
        except ApiException as e:
            self.handle_api_exception(e, "get", "ConfigMap", name, namespace)
