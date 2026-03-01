"""Role service for managing Role and ClusterRole CRD resources."""

import logging
import time
from typing import Optional

from app.models.role import Role, ClusterRole, RoleSpec
from app.repositories.rbac_repository import RBACRepository
from app.repositories.namespace_repository import NamespaceRepository
from app.validators import validate_role_name, validate_role_spec
from app.exceptions import (
    ResourceNotFoundError,
    ValidationError,
)
from app.utils.audit import AuditLogger

logger = logging.getLogger(__name__)


class RoleService:
    """Service for managing Role and ClusterRole CRD lifecycle."""

    # Retry configuration for namespace checks
    MAX_RETRIES = 2
    RETRY_DELAY_SECONDS = 5

    def __init__(
        self,
        rbac_repo: RBACRepository,
        ns_repo: NamespaceRepository,
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the service with required dependencies.

        Args:
            rbac_repo: Repository for RBAC operations
            ns_repo: Repository for Namespace operations
            audit_logger: Optional audit logger for tracking changes
        """
        self.rbac_repo = rbac_repo
        self.ns_repo = ns_repo
        self.audit = audit_logger

    def create_role(self, body: dict, spec: dict, namespace: str) -> dict:
        """Handle Role CRD creation.

        Args:
            body: The full Kopf body object
            spec: The spec portion of the CRD
            namespace: The namespace where the Role should be created

        Returns:
            Status dict for Kopf
        """
        kind = body.get('kind', 'Role')
        name = body['metadata']['name']

        # Validate inputs
        validate_role_name(name)
        validated_spec = validate_role_spec(spec)

        if kind == 'Role':
            return self._create_namespaced_role(name, namespace, validated_spec)
        elif kind == 'ClusterRole':
            return self._create_cluster_role(name, validated_spec)
        else:
            logger.warning(f"Unsupported kind '{kind}'")
            return {"status": "error", "message": f"Unsupported kind: {kind}"}

    def _create_namespaced_role(self, name: str, namespace: str,
                                 spec: dict) -> dict:
        """Create a namespaced Role.

        Args:
            name: The role name
            namespace: The namespace
            spec: Validated spec dict

        Returns:
            Status dict
        """
        # Wait for namespace to exist
        if not self._wait_for_namespace(namespace):
            return {
                "status": "error",
                "message": f"Namespace '{namespace}' does not exist"
            }

        rules = spec.get('rules', [])

        # Check if role exists
        if self.rbac_repo.role_exists(name, namespace):
            self.rbac_repo.update_role(name, namespace, rules)
            logger.info(f"Updated Role '{name}' in namespace '{namespace}'")
            action = "updated"
        else:
            self.rbac_repo.create_role(name, namespace, rules)
            logger.info(f"Created Role '{name}' in namespace '{namespace}'")
            action = "created"

        if self.audit:
            if action == "created":
                self.audit.log_create(
                    resource_type="Role",
                    name=name,
                    namespace=namespace,
                    details={"rules_count": len(rules)}
                )
            else:
                self.audit.log_update(
                    resource_type="Role",
                    name=name,
                    namespace=namespace,
                    details={"rules_count": len(rules)}
                )

        return {"status": action, "role": name, "namespace": namespace}

    def _create_cluster_role(self, name: str, spec: dict) -> dict:
        """Create a ClusterRole.

        Args:
            name: The cluster role name
            spec: Validated spec dict

        Returns:
            Status dict
        """
        rules = spec.get('rules', [])

        # Check if cluster role exists
        if self.rbac_repo.cluster_role_exists(name):
            self.rbac_repo.update_cluster_role(name, rules)
            logger.info(f"Updated ClusterRole '{name}'")
            action = "updated"
        else:
            self.rbac_repo.create_cluster_role(name, rules)
            logger.info(f"Created ClusterRole '{name}'")
            action = "created"

        if self.audit:
            if action == "created":
                self.audit.log_create(
                    resource_type="ClusterRole",
                    name=name,
                    details={"rules_count": len(rules)}
                )
            else:
                self.audit.log_update(
                    resource_type="ClusterRole",
                    name=name,
                    details={"rules_count": len(rules)}
                )

        return {"status": action, "clusterRole": name}

    def _wait_for_namespace(self, namespace: str) -> bool:
        """Wait for a namespace to exist with retries.

        Args:
            namespace: The namespace name

        Returns:
            True if namespace exists, False after all retries exhausted
        """
        for attempt in range(self.MAX_RETRIES + 1):
            if self.ns_repo.exists(namespace):
                return True

            if attempt < self.MAX_RETRIES:
                logger.warning(
                    f"Namespace '{namespace}' not found, "
                    f"retrying in {self.RETRY_DELAY_SECONDS}s..."
                )
                time.sleep(self.RETRY_DELAY_SECONDS)

        logger.error(
            f"Namespace '{namespace}' does not exist after "
            f"{self.MAX_RETRIES} retries"
        )
        return False

    def delete_role(self, body: dict, namespace: str) -> dict:
        """Handle Role/ClusterRole CRD deletion.

        Args:
            body: The full Kopf body object
            namespace: The namespace (for Role only)

        Returns:
            Status dict for Kopf
        """
        kind = body.get('kind', 'Role')
        name = body['metadata']['name']

        if kind == 'Role':
            return self._delete_namespaced_role(name, namespace)
        elif kind == 'ClusterRole':
            return self._delete_cluster_role(name)
        else:
            logger.warning(f"Unsupported kind '{kind}'")
            return {"status": "error", "message": f"Unsupported kind: {kind}"}

    def _delete_namespaced_role(self, name: str, namespace: str) -> dict:
        """Delete a namespaced Role.

        Args:
            name: The role name
            namespace: The namespace

        Returns:
            Status dict
        """
        try:
            self.rbac_repo.delete_role(name, namespace)
            logger.info(f"Deleted Role '{name}' from namespace '{namespace}'")

            if self.audit:
                self.audit.log_delete(
                    resource_type="Role",
                    name=name,
                    namespace=namespace
                )

            return {"status": "deleted", "role": name}
        except ResourceNotFoundError:
            logger.info(f"Role '{name}' already deleted")
            return {"status": "already_deleted", "role": name}

    def _delete_cluster_role(self, name: str) -> dict:
        """Delete a ClusterRole.

        Args:
            name: The cluster role name

        Returns:
            Status dict
        """
        try:
            self.rbac_repo.delete_cluster_role(name)
            logger.info(f"Deleted ClusterRole '{name}'")

            if self.audit:
                self.audit.log_delete(
                    resource_type="ClusterRole",
                    name=name
                )

            return {"status": "deleted", "clusterRole": name}
        except ResourceNotFoundError:
            logger.info(f"ClusterRole '{name}' already deleted")
            return {"status": "already_deleted", "clusterRole": name}
