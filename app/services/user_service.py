"""User service for managing User CRD resources."""

import logging
from typing import Optional

from app.models.user import User
from app.repositories.serviceaccount_repository import ServiceAccountRepository
from app.repositories.namespace_repository import NamespaceRepository
from app.repositories.secret_repository import SecretRepository
from app.services.rbac_service import RBACService
from app.services.kubeconfig_service import KubeconfigService
from app.validators import validate_user_name, validate_user_spec
from app.exceptions import ResourceNotFoundError
from app.utils.audit import AuditLogger

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing User CRD lifecycle."""

    def __init__(
        self,
        sa_repo: ServiceAccountRepository,
        ns_repo: NamespaceRepository,
        secret_repo: SecretRepository,
        rbac_service: RBACService,
        kubeconfig_service: KubeconfigService,
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the service with required dependencies.

        Args:
            sa_repo: Repository for ServiceAccount operations
            ns_repo: Repository for Namespace operations
            secret_repo: Repository for Secret operations
            rbac_service: Service for RBAC operations
            kubeconfig_service: Service for kubeconfig generation
            audit_logger: Optional audit logger for tracking changes
        """
        self.sa_repo = sa_repo
        self.ns_repo = ns_repo
        self.secret_repo = secret_repo
        self.rbac_service = rbac_service
        self.kubeconfig_service = kubeconfig_service
        self.audit = audit_logger

    def create_user(self, body: dict, spec: dict, namespace: str) -> dict:
        """Handle User CRD creation.

        Args:
            body: The full Kopf body object
            spec: The spec portion of the CRD
            namespace: The namespace where the User was created

        Returns:
            Status dict for Kopf

        Raises:
            ValidationError: If input validation fails
            OperatorError: If any operation fails
        """
        user = User.from_dict(body)

        # Validate inputs
        validate_user_name(user.name)
        validate_user_spec(spec)

        logger.info(f"Creating user '{user.name}' in namespace '{namespace}'")

        # Create ServiceAccount
        self.sa_repo.create(
            name=user.service_account_name,
            namespace=namespace
        )
        logger.info(f"Created ServiceAccount '{user.service_account_name}'")

        if self.audit:
            self.audit.log_create(
                resource_type="ServiceAccount",
                name=user.service_account_name,
                namespace=namespace,
                details={"user": user.name}
            )

        # If enabled, set up full user resources
        if user.spec.enabled:
            self._setup_enabled_user(user)

        # Create role bindings
        self.rbac_service.create_user_role_bindings(user)

        return {"status": "created", "serviceAccount": user.service_account_name}

    def _setup_enabled_user(self, user: User) -> None:
        """Set up resources for an enabled user.

        This includes:
        - Service account token secret
        - Restricted namespace permissions
        - User namespace
        - Kubeconfig secret

        Args:
            user: The User object
        """
        # Create SA token secret
        self.secret_repo.create_service_account_token(
            sa_name=user.service_account_name,
            namespace=user.namespace
        )
        logger.info(f"Created SA token secret for '{user.name}'")

        # Create restricted permissions
        self.rbac_service.create_user_restricted_permissions(user)

        # Create/ensure user namespace exists
        self.ns_repo.ensure_exists(user.user_namespace)
        logger.info(f"Ensured namespace '{user.user_namespace}' exists")

        # Generate kubeconfig
        self.kubeconfig_service.create_kubeconfig_secret(user)

    def update_user(self, body: dict, spec: dict, namespace: str) -> dict:
        """Handle User CRD update.

        Args:
            body: The full Kopf body object
            spec: The spec portion of the CRD
            namespace: The namespace where the User exists

        Returns:
            Status dict for Kopf
        """
        user = User.from_dict(body)

        # Validate inputs
        validate_user_name(user.name)
        validate_user_spec(spec)

        logger.info(f"Updating user '{user.name}' in namespace '{namespace}'")

        # Update ServiceAccount (if needed)
        try:
            self.sa_repo.update(
                name=user.service_account_name,
                namespace=namespace
            )
        except ResourceNotFoundError:
            # SA was deleted, recreate
            self.sa_repo.create(
                name=user.service_account_name,
                namespace=namespace
            )

        # Handle enabled/disabled state change
        if user.spec.enabled:
            self._setup_enabled_user(user)
        else:
            self._cleanup_disabled_user(user)

        # Update role bindings
        self.rbac_service.update_user_role_bindings(user)

        if self.audit:
            self.audit.log_update(
                resource_type="User",
                name=user.name,
                namespace=namespace,
                details={"enabled": user.spec.enabled}
            )

        return {"status": "updated", "serviceAccount": user.service_account_name}

    def _cleanup_disabled_user(self, user: User) -> None:
        """Clean up resources when user is disabled.

        This removes the user namespace (and all resources in it).

        Args:
            user: The User object
        """
        try:
            self.ns_repo.delete(user.user_namespace)
            logger.info(f"Deleted user namespace '{user.user_namespace}'")
        except ResourceNotFoundError:
            logger.debug(f"User namespace '{user.user_namespace}' already deleted")

    def delete_user(self, body: dict, spec: dict, namespace: str) -> dict:
        """Handle User CRD deletion.

        Args:
            body: The full Kopf body object
            spec: The spec portion of the CRD
            namespace: The namespace where the User exists

        Returns:
            Status dict for Kopf
        """
        user = User.from_dict(body)

        logger.info(f"Deleting user '{user.name}' from namespace '{namespace}'")

        # Delete ServiceAccount
        try:
            self.sa_repo.delete(
                name=user.service_account_name,
                namespace=namespace
            )
            logger.info(f"Deleted ServiceAccount '{user.service_account_name}'")

            if self.audit:
                self.audit.log_delete(
                    resource_type="ServiceAccount",
                    name=user.service_account_name,
                    namespace=namespace
                )
        except ResourceNotFoundError:
            logger.debug(f"ServiceAccount '{user.service_account_name}' already deleted")

        # Delete user namespace if enabled
        if user.spec.enabled:
            try:
                self.ns_repo.delete(user.user_namespace)
                logger.info(f"Deleted user namespace '{user.user_namespace}'")
            except ResourceNotFoundError:
                logger.debug(f"User namespace '{user.user_namespace}' already deleted")

        # Delete all role bindings
        self.rbac_service.delete_user_role_bindings(user)

        # Delete restricted permissions
        self.rbac_service.delete_user_restricted_permissions(user)

        return {"status": "deleted"}
