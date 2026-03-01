"""User service for managing User CRD resources."""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.models.user import User, NetworkPolicyMode
from app.repositories.serviceaccount_repository import ServiceAccountRepository
from app.repositories.namespace_repository import NamespaceRepository
from app.repositories.secret_repository import SecretRepository
from app.repositories.resource_quota_repository import ResourceQuotaRepository
from app.repositories.network_policy_repository import NetworkPolicyRepository
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
        quota_repo: Optional[ResourceQuotaRepository] = None,
        network_policy_repo: Optional[NetworkPolicyRepository] = None,
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the service with required dependencies.

        Args:
            sa_repo: Repository for ServiceAccount operations
            ns_repo: Repository for Namespace operations
            secret_repo: Repository for Secret operations
            rbac_service: Service for RBAC operations
            kubeconfig_service: Service for kubeconfig generation
            quota_repo: Optional repository for ResourceQuota operations
            network_policy_repo: Optional repository for NetworkPolicy operations
            audit_logger: Optional audit logger for tracking changes
        """
        self.sa_repo = sa_repo
        self.ns_repo = ns_repo
        self.secret_repo = secret_repo
        self.rbac_service = rbac_service
        self.kubeconfig_service = kubeconfig_service
        self.quota_repo = quota_repo
        self.network_policy_repo = network_policy_repo
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

        user_type = "human" if user.spec.is_human else "serviceAccount"
        logger.info(
            f"Creating {user_type} user '{user.name}' "
            f"(type={user.spec.user_type.value})"
        )

        # Determine SA namespace
        sa_namespace = user.sa_namespace

        # Create ServiceAccount
        self.sa_repo.create(
            name=user.service_account_name,
            namespace=sa_namespace
        )
        logger.info(
            f"Created ServiceAccount '{user.service_account_name}' "
            f"in namespace '{sa_namespace}'"
        )

        if self.audit:
            self.audit.log_create(
                resource_type="ServiceAccount",
                name=user.service_account_name,
                namespace=sa_namespace,
                details={
                    "user": user.name,
                    "user_type": user_type
                }
            )

        # Set up resources based on user type
        if user.spec.is_human:
            self._setup_human_user(user)
        else:
            logger.info(
                f"ServiceAccount user '{user.name}' created in '{sa_namespace}'"
            )

        # Create role bindings
        self.rbac_service.create_user_role_bindings(user)

        # Build status
        status = {
            "state": "ready",
            "message": f"User '{user.name}' created successfully",
            "serviceAccount": user.service_account_name,
            "namespace": sa_namespace,
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        }

        if user.spec.is_human:
            status["kubeconfigSecret"] = user.kubeconfig_secret_name

        return status

    def _setup_human_user(self, user: User) -> None:
        """Set up resources for a human user.

        This includes:
        - Service account token secret
        - Restricted namespace permissions
        - User namespace (with optional quota and network policy)
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

        # Create/ensure user namespace exists with optional config
        ns_labels = {}
        ns_annotations = {}

        if user.spec.namespace_config:
            ns_labels = user.spec.namespace_config.labels.copy()
            ns_annotations = user.spec.namespace_config.annotations.copy()

        # Add standard labels
        ns_labels.update({
            "app.kubernetes.io/managed-by": "k8s-iam-operator",
            "k8sio.auth/user": user.name,
            "k8sio.auth/type": "human",
        })

        self.ns_repo.ensure_exists(
            user.user_namespace,
            labels=ns_labels,
            annotations=ns_annotations
        )
        logger.info(f"Ensured namespace '{user.user_namespace}' exists")

        # Apply ResourceQuota if configured
        if (
            user.spec.namespace_config
            and user.spec.namespace_config.quota
            and not user.spec.namespace_config.quota.is_empty()
            and self.quota_repo
        ):
            quota_spec = user.spec.namespace_config.quota.to_dict()
            self.quota_repo.ensure_exists(
                name=user.quota_name,
                namespace=user.user_namespace,
                hard=quota_spec,
                labels={"app.kubernetes.io/managed-by": "k8s-iam-operator"}
            )
            logger.info(
                f"Applied ResourceQuota '{user.quota_name}' "
                f"to namespace '{user.user_namespace}'"
            )

        # Apply NetworkPolicy if configured
        if (
            user.spec.namespace_config
            and user.spec.namespace_config.network_policy != NetworkPolicyMode.NONE
            and self.network_policy_repo
        ):
            policy_mode = user.spec.namespace_config.network_policy
            if policy_mode == NetworkPolicyMode.ISOLATED:
                self.network_policy_repo.create_isolated_policy(
                    name=user.network_policy_name,
                    namespace=user.user_namespace,
                    labels={"app.kubernetes.io/managed-by": "k8s-iam-operator"}
                )
            elif policy_mode == NetworkPolicyMode.RESTRICTED:
                self.network_policy_repo.create_restricted_policy(
                    name=user.network_policy_name,
                    namespace=user.user_namespace,
                    labels={"app.kubernetes.io/managed-by": "k8s-iam-operator"}
                )
            logger.info(
                f"Applied NetworkPolicy '{user.network_policy_name}' "
                f"({policy_mode.value}) to namespace '{user.user_namespace}'"
            )

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

        user_type = "human" if user.spec.is_human else "serviceAccount"
        logger.info(f"Updating {user_type} user '{user.name}'")

        sa_namespace = user.sa_namespace

        # Update ServiceAccount (if needed)
        try:
            self.sa_repo.update(
                name=user.service_account_name,
                namespace=sa_namespace
            )
        except ResourceNotFoundError:
            # SA was deleted, recreate
            self.sa_repo.create(
                name=user.service_account_name,
                namespace=sa_namespace
            )

        # Handle type changes
        if user.spec.is_human:
            self._setup_human_user(user)
        else:
            self._cleanup_human_resources(user)

        # Update role bindings
        self.rbac_service.update_user_role_bindings(user)

        if self.audit:
            self.audit.log_update(
                resource_type="User",
                name=user.name,
                namespace=namespace,
                details={
                    "type": user_type,
                    "is_human": user.spec.is_human
                }
            )

        # Build status
        status = {
            "state": "ready",
            "message": f"User '{user.name}' updated successfully",
            "serviceAccount": user.service_account_name,
            "namespace": sa_namespace,
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        }

        if user.spec.is_human:
            status["kubeconfigSecret"] = user.kubeconfig_secret_name

        return status

    def _cleanup_human_resources(self, user: User) -> None:
        """Clean up human-specific resources when user type changes.

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

        user_type = "human" if user.spec.is_human else "serviceAccount"
        logger.info(f"Deleting {user_type} user '{user.name}'")

        sa_namespace = user.sa_namespace

        # Delete ServiceAccount
        try:
            self.sa_repo.delete(
                name=user.service_account_name,
                namespace=sa_namespace
            )
            logger.info(f"Deleted ServiceAccount '{user.service_account_name}'")

            if self.audit:
                self.audit.log_delete(
                    resource_type="ServiceAccount",
                    name=user.service_account_name,
                    namespace=sa_namespace
                )
        except ResourceNotFoundError:
            logger.debug(
                f"ServiceAccount '{user.service_account_name}' already deleted"
            )

        # Delete user namespace if human user
        if user.spec.is_human:
            try:
                self.ns_repo.delete(user.user_namespace)
                logger.info(f"Deleted user namespace '{user.user_namespace}'")
            except ResourceNotFoundError:
                logger.debug(
                    f"User namespace '{user.user_namespace}' already deleted"
                )

        # Delete all role bindings
        self.rbac_service.delete_user_role_bindings(user)

        # Delete restricted permissions
        self.rbac_service.delete_user_restricted_permissions(user)

        return {"state": "deleted"}
