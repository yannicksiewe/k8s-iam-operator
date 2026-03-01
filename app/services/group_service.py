"""Group service for managing Group CRD resources."""

import logging
from typing import Optional

from kubernetes import client
from kubernetes.client.rest import ApiException

from app.models.group import Group
from app.config import Config
from app.services.rbac_service import RBACService
from app.validators import validate_group_name, validate_group_spec
from app.exceptions import (
    OperatorError,
    ResourceNotFoundError,
    KubernetesAPIError,
)
from app.utils.audit import AuditLogger

logger = logging.getLogger(__name__)


class GroupService:
    """Service for managing Group CRD lifecycle."""

    def __init__(
        self,
        rbac_service: RBACService,
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the service with required dependencies.

        Args:
            rbac_service: Service for RBAC operations
            audit_logger: Optional audit logger for tracking changes
        """
        self.rbac_service = rbac_service
        self.audit = audit_logger

    def create_group(self, body: dict, spec: dict, namespace: str) -> dict:
        """Handle Group CRD creation.

        Args:
            body: The full Kopf body object
            spec: The spec portion of the CRD
            namespace: The namespace where the Group was created

        Returns:
            Status dict for Kopf
        """
        group = Group.from_dict(body)

        # Validate inputs
        validate_group_name(group.name)
        validate_group_spec(spec)

        logger.info(f"Creating group '{group.name}' in namespace '{namespace}'")

        # Create all role bindings for the group
        self.rbac_service.create_group_role_bindings(group)

        if self.audit:
            self.audit.log_create(
                resource_type="Group",
                name=group.name,
                namespace=namespace,
                details={
                    "cluster_roles": len(group.spec.cluster_roles),
                    "roles": len(group.spec.roles)
                }
            )

        return {
            "status": "created",
            "bindings": len(group.spec.cluster_roles) + len(group.spec.roles)
        }

    def update_group(self, body: dict, spec: dict, namespace: str) -> dict:
        """Handle Group CRD update.

        Args:
            body: The full Kopf body object
            spec: The spec portion of the CRD
            namespace: The namespace where the Group exists

        Returns:
            Status dict for Kopf
        """
        group = Group.from_dict(body)

        # Validate inputs
        validate_group_name(group.name)
        validate_group_spec(spec)

        logger.info(f"Updating group '{group.name}' in namespace '{namespace}'")

        # Update role bindings (removes stale ones, creates new ones)
        self.rbac_service.update_group_role_bindings(group)

        if self.audit:
            self.audit.log_update(
                resource_type="Group",
                name=group.name,
                namespace=namespace,
                details={
                    "cluster_roles": len(group.spec.cluster_roles),
                    "roles": len(group.spec.roles)
                }
            )

        return {
            "status": "updated",
            "bindings": len(group.spec.cluster_roles) + len(group.spec.roles)
        }

    def delete_group(self, body: dict, namespace: str) -> dict:
        """Handle Group CRD deletion.

        Args:
            body: The full Kopf body object
            namespace: The namespace where the Group exists

        Returns:
            Status dict for Kopf
        """
        group = Group.from_dict(body)

        logger.info(f"Deleting group '{group.name}' from namespace '{namespace}'")

        # Delete all role bindings for the group
        self.rbac_service.delete_group_role_bindings(group)

        # Delete the custom resource itself
        self._delete_custom_resource(group)

        if self.audit:
            self.audit.log_delete(
                resource_type="Group",
                name=group.name,
                namespace=namespace
            )

        return {"status": "deleted"}

    def _delete_custom_resource(self, group: Group) -> None:
        """Delete the Group custom resource.

        Args:
            group: The Group object
        """
        try:
            custom_api = client.CustomObjectsApi()
            custom_api.delete_namespaced_custom_object(
                group=Config.GROUP,
                version=Config.VERSION,
                namespace=group.namespace,
                plural="groups",
                name=group.name,
                body=client.V1DeleteOptions(),
            )
            logger.info(f"Deleted Group custom resource '{group.name}'")
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error deleting Group custom resource: {e.reason}")
            else:
                logger.debug(f"Group custom resource '{group.name}' already deleted")
