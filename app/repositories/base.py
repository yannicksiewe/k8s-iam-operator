"""Base repository with common Kubernetes client setup."""

from typing import Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from app.exceptions import KubernetesAPIError, ResourceNotFoundError, ResourceAlreadyExistsError


class BaseRepository:
    """Base class for all Kubernetes repositories.

    Provides common client initialization and error handling.
    """

    _api_client: Optional[client.ApiClient] = None

    def __init__(self, api_client: Optional[client.ApiClient] = None):
        """Initialize repository with optional API client.

        Args:
            api_client: Optional pre-configured API client. If not provided,
                       will use the default configured client.
        """
        if api_client:
            self._api_client = api_client
        elif BaseRepository._api_client is None:
            BaseRepository._api_client = self._configure_client()

    @staticmethod
    def _configure_client() -> client.ApiClient:
        """Configure Kubernetes client for in-cluster or local environments."""
        try:
            config.load_incluster_config()
            in_cluster = True
        except config.ConfigException:
            config.load_kube_config()
            in_cluster = False

        configuration = client.Configuration()

        if in_cluster:
            token_path = '/var/run/secrets/kubernetes.io/serviceaccount/token'
            with open(token_path, 'r') as f:
                token = f.read().strip()
            configuration.api_key['authorization'] = 'Bearer ' + token
            configuration.ssl_ca_cert = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
            configuration.host = 'https://kubernetes.default.svc'
        else:
            configuration = client.Configuration.get_default_copy()

        configuration.verify_ssl = True
        configuration.debug = False

        return client.ApiClient(configuration)

    @property
    def api_client(self) -> client.ApiClient:
        """Get the API client."""
        if self._api_client is None:
            BaseRepository._api_client = self._configure_client()
        return BaseRepository._api_client

    @staticmethod
    def handle_api_exception(e: ApiException, operation: str, resource_type: str,
                              name: str, namespace: Optional[str] = None) -> None:
        """Handle Kubernetes API exceptions consistently.

        Args:
            e: The ApiException that was raised
            operation: The operation being performed (create, get, delete, etc.)
            resource_type: Type of resource (ServiceAccount, Namespace, etc.)
            name: Name of the resource
            namespace: Optional namespace of the resource

        Raises:
            ResourceNotFoundError: If the resource was not found (404)
            ResourceAlreadyExistsError: If the resource already exists (409)
            KubernetesAPIError: For other API errors
        """
        if e.status == 404:
            raise ResourceNotFoundError(resource_type, name, namespace)
        elif e.status == 409:
            raise ResourceAlreadyExistsError(resource_type, name, namespace)
        else:
            raise KubernetesAPIError(
                operation=operation,
                message=f"Failed to {operation} {resource_type} '{name}': {e.reason}",
                status_code=e.status
            )
