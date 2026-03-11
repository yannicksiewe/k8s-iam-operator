"""Kubeconfig service for generating user kubeconfig files."""

import base64
import json
import logging
from typing import Optional

from app.models.user import User
from app.repositories.secret_repository import SecretRepository
from app.exceptions import KubeconfigGenerationError, ResourceNotFoundError
from app.utils.audit import AuditLogger

logger = logging.getLogger(__name__)


class KubeconfigService:
    """Service for generating and managing kubeconfig secrets."""

    def __init__(
        self,
        secret_repo: SecretRepository,
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the service with required repositories.

        Args:
            secret_repo: Repository for secret operations
            audit_logger: Optional audit logger for tracking changes
        """
        self.secret_repo = secret_repo
        self.audit = audit_logger

    def generate_kubeconfig(self, user: User) -> str:
        """Generate a kubeconfig for the given user.

        Args:
            user: The User object

        Returns:
            The kubeconfig as a JSON string

        Raises:
            KubeconfigGenerationError: If generation fails
        """
        try:
            # Get the service account token
            token_secret = self.secret_repo.get(
                name=user.token_secret_name,
                namespace=user.namespace
            )
            token = token_secret.data.get("token")
            if not token:
                raise KubeconfigGenerationError(
                    user.name,
                    f"Token secret '{user.token_secret_name}' has no token data"
                )

            # Get cluster CA certificate
            ca_configmap = self.secret_repo.get_configmap(
                name='kube-root-ca.crt',
                namespace='kube-system'
            )
            cluster_ca = ca_configmap.data.get('ca.crt')
            if not cluster_ca:
                raise KubeconfigGenerationError(
                    user.name,
                    "Could not retrieve cluster CA certificate"
                )

            # Get cluster URL from API client configuration
            api_client = self.secret_repo.api_client
            cluster_url = api_client.configuration.host

            # Build kubeconfig structure
            kubeconfig = {
                'apiVersion': 'v1',
                'kind': 'Config',
                'clusters': [{
                    'cluster': {
                        'server': cluster_url,
                        'certificate-authority-data': base64.b64encode(
                            cluster_ca.encode('utf-8')
                        ).decode('utf-8'),
                    },
                    'name': 'cluster',
                }],
                'contexts': [{
                    'context': {
                        'cluster': 'cluster',
                        'user': user.name,
                    },
                    'name': f'{user.name}-context',
                }],
                'current-context': f'{user.name}-context',
                'users': [{
                    'name': user.name,
                    'user': {
                        'token': base64.b64decode(token).decode('utf-8'),
                    },
                }],
            }

            return json.dumps(kubeconfig)

        except ResourceNotFoundError as e:
            raise KubeconfigGenerationError(
                user.name,
                f"Required resource not found: {e.message}"
            )
        except Exception as e:
            raise KubeconfigGenerationError(
                user.name,
                f"Failed to generate kubeconfig: {str(e)}"
            )

    def create_kubeconfig_secret(self, user: User) -> None:
        """Create or update a kubeconfig secret for the user.

        The secret is created in the user's dedicated namespace.
        If the secret already exists, it will be updated.

        Args:
            user: The User object

        Raises:
            KubeconfigGenerationError: If creation fails
        """
        try:
            kubeconfig = self.generate_kubeconfig(user)
            kubeconfig_b64 = base64.b64encode(
                kubeconfig.encode('utf-8')
            ).decode('utf-8')

            self.secret_repo.ensure_kubeconfig_secret(
                name=user.kubeconfig_secret_name,
                namespace=user.user_namespace,
                kubeconfig_data=kubeconfig_b64
            )

            logger.info(
                f"Ensured kubeconfig secret '{user.kubeconfig_secret_name}' "
                f"in namespace '{user.user_namespace}'"
            )

            if self.audit:
                self.audit.log_create(
                    resource_type="Secret",
                    name=user.kubeconfig_secret_name,
                    namespace=user.user_namespace,
                    details={"type": "kubeconfig", "user": user.name}
                )

        except Exception as e:
            if isinstance(e, KubeconfigGenerationError):
                raise
            raise KubeconfigGenerationError(
                user.name,
                f"Failed to create kubeconfig secret: {str(e)}"
            )

    def delete_kubeconfig_secret(self, user: User) -> None:
        """Delete the kubeconfig secret for a user.

        Args:
            user: The User object
        """
        try:
            self.secret_repo.delete(
                name=user.kubeconfig_secret_name,
                namespace=user.user_namespace
            )
            logger.info(
                f"Deleted kubeconfig secret '{user.kubeconfig_secret_name}' "
                f"from namespace '{user.user_namespace}'"
            )

            if self.audit:
                self.audit.log_delete(
                    resource_type="Secret",
                    name=user.kubeconfig_secret_name,
                    namespace=user.user_namespace
                )
        except ResourceNotFoundError:
            logger.debug(
                f"Kubeconfig secret '{user.kubeconfig_secret_name}' "
                f"not found, skipping deletion"
            )

    def kubeconfig_exists(self, user: User) -> bool:
        """Check if a kubeconfig secret exists for the user.

        Args:
            user: The User object

        Returns:
            True if the kubeconfig secret exists
        """
        return self.secret_repo.exists(
            name=user.kubeconfig_secret_name,
            namespace=user.user_namespace
        )
