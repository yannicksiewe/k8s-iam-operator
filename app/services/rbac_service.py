"""RBAC service for managing role bindings."""

import logging
from typing import Optional, Set, Tuple

from app.models.user import User, ClusterRoleBinding as CRoleBinding
from app.models.group import Group
from app.repositories.rbac_repository import RBACRepository
from app.repositories.namespace_repository import NamespaceRepository
from app.exceptions import ResourceNotFoundError
from app.utils.audit import AuditLogger

logger = logging.getLogger(__name__)


class RBACService:
    """Service for managing RBAC bindings."""

    def __init__(
        self,
        rbac_repo: RBACRepository,
        ns_repo: NamespaceRepository,
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the service with required repositories.

        Args:
            rbac_repo: Repository for RBAC operations
            ns_repo: Repository for namespace operations
            audit_logger: Optional audit logger for tracking changes
        """
        self.rbac_repo = rbac_repo
        self.ns_repo = ns_repo
        self.audit = audit_logger

    # ==================== User RBAC ====================

    def create_user_role_bindings(self, user: User) -> None:
        """Create all role bindings for a user.

        Args:
            user: The User object
        """
        # Create RoleBindings for ClusterRoles in specific namespaces
        for cr_binding in user.spec.cluster_roles:
            if cr_binding.namespace:
                self._create_user_namespaced_binding(user, cr_binding)

        # Create RoleBindings for Roles
        for role_name in user.spec.roles:
            self._create_user_role_binding(user, role_name)

    def _create_user_namespaced_binding(self, user: User,
                                         cr_binding: CRoleBinding) -> None:
        """Create a RoleBinding for a ClusterRole in a namespace."""
        binding_name = f"{user.name}-{cr_binding.namespace}-{cr_binding.cluster_role}"

        # Verify namespace exists
        if not self.ns_repo.exists(cr_binding.namespace):
            logger.warning(f"Namespace '{cr_binding.namespace}' does not exist")
            return

        # Verify ClusterRole exists
        if not self.rbac_repo.cluster_role_exists(cr_binding.cluster_role):
            logger.warning(f"ClusterRole '{cr_binding.cluster_role}' does not exist")
            return

        # Build subjects list
        subjects = [
            self.rbac_repo.create_service_account_subject(user.name, user.namespace)
        ]
        if cr_binding.group:
            subjects.append(
                self.rbac_repo.create_group_subject(cr_binding.group)
            )

        role_ref = self.rbac_repo.create_cluster_role_ref(cr_binding.cluster_role)

        self.rbac_repo.create_or_update_role_binding(
            name=binding_name,
            namespace=cr_binding.namespace,
            role_ref=role_ref,
            subjects=subjects
        )
        logger.info(f"Created RoleBinding '{binding_name}' in namespace '{cr_binding.namespace}'")

        if self.audit:
            self.audit.log_create(
                resource_type="RoleBinding",
                name=binding_name,
                namespace=cr_binding.namespace,
                details={"user": user.name, "clusterRole": cr_binding.cluster_role}
            )

    def _create_user_role_binding(self, user: User, role_name: str) -> None:
        """Create a RoleBinding for a Role in the user's namespace."""
        binding_name = f"{user.name}-{user.namespace}-{role_name}"

        # Verify namespace exists
        if not self.ns_repo.exists(user.namespace):
            logger.warning(f"Namespace '{user.namespace}' does not exist")
            return

        # Verify Role exists
        if not self.rbac_repo.role_exists(role_name, user.namespace):
            logger.warning(f"Role '{role_name}' does not exist in namespace '{user.namespace}'")
            return

        subject = self.rbac_repo.create_service_account_subject(user.name, user.namespace)
        role_ref = self.rbac_repo.create_role_ref(role_name)

        self.rbac_repo.create_or_update_role_binding(
            name=binding_name,
            namespace=user.namespace,
            role_ref=role_ref,
            subjects=[subject]
        )
        logger.info(f"Created RoleBinding '{binding_name}' for role '{role_name}'")

        if self.audit:
            self.audit.log_create(
                resource_type="RoleBinding",
                name=binding_name,
                namespace=user.namespace,
                details={"user": user.name, "role": role_name}
            )

    def update_user_role_bindings(self, user: User) -> None:
        """Update role bindings for a user, removing stale ones.

        Args:
            user: The User object
        """
        # Remove stale bindings
        self._cleanup_user_bindings(user)

        # Create/update current bindings
        self.create_user_role_bindings(user)

    def _cleanup_user_bindings(self, user: User) -> None:
        """Remove RoleBindings that are no longer in the user spec."""
        # Get expected binding keys
        expected_bindings: Set[Tuple[str, str]] = set()
        for cr in user.spec.cluster_roles:
            if cr.namespace:
                expected_bindings.add((cr.namespace, cr.cluster_role))

        # Find and delete stale bindings
        bindings = self.rbac_repo.find_bindings_for_subject(
            subject_name=user.name,
            subject_kind="ServiceAccount"
        )

        for binding in bindings:
            ns = binding.metadata.namespace
            role_name = binding.role_ref.name

            # Check if this binding should exist
            if binding.role_ref.kind == "ClusterRole":
                if (ns, role_name) not in expected_bindings:
                    self._delete_role_binding(binding.metadata.name, ns)

    def _delete_role_binding(self, name: str, namespace: str) -> None:
        """Delete a RoleBinding with logging."""
        try:
            self.rbac_repo.delete_role_binding(name, namespace)
            logger.info(f"Deleted RoleBinding '{name}' from namespace '{namespace}'")

            if self.audit:
                self.audit.log_delete(
                    resource_type="RoleBinding",
                    name=name,
                    namespace=namespace
                )
        except ResourceNotFoundError:
            logger.debug(f"RoleBinding '{name}' already deleted")

    def delete_user_role_bindings(self, user: User) -> None:
        """Delete all role bindings for a user.

        Args:
            user: The User object
        """
        # Delete namespaced RoleBindings
        bindings = self.rbac_repo.find_bindings_for_subject(
            subject_name=user.name,
            subject_kind="ServiceAccount"
        )
        for binding in bindings:
            self._delete_role_binding(
                binding.metadata.name,
                binding.metadata.namespace
            )

        # Delete ClusterRoleBindings
        crb_bindings = self.rbac_repo.find_cluster_role_bindings_for_subject(
            subject_name=user.name,
            subject_kind="ServiceAccount"
        )
        for binding in crb_bindings:
            self._delete_cluster_role_binding(binding.metadata.name)

    def _delete_cluster_role_binding(self, name: str) -> None:
        """Delete a ClusterRoleBinding with logging."""
        try:
            self.rbac_repo.delete_cluster_role_binding(name)
            logger.info(f"Deleted ClusterRoleBinding '{name}'")

            if self.audit:
                self.audit.log_delete(
                    resource_type="ClusterRoleBinding",
                    name=name
                )
        except ResourceNotFoundError:
            logger.debug(f"ClusterRoleBinding '{name}' already deleted")

    # ==================== User Restricted Permissions ====================

    def create_user_restricted_permissions(self, user: User) -> None:
        """Create restricted namespace ClusterRole and binding for a user.

        This restricts the user's access to only the namespaces in their CRoles spec.

        Args:
            user: The User object
        """
        # Build list of allowed namespaces
        namespaces = list(set(
            [cr.namespace for cr in user.spec.cluster_roles if cr.namespace] +
            ["default", user.user_namespace]
        ))

        # Create ClusterRole
        rules = [{
            "apiGroups": [""],
            "resources": ["namespaces"],
            "verbs": ["get", "watch", "list"],
            "resourceNames": namespaces
        }]

        self.rbac_repo.create_or_update_cluster_role(
            name=user.restricted_role_name,
            rules=rules
        )
        logger.info(f"Created restricted ClusterRole '{user.restricted_role_name}'")

        # Create ClusterRoleBinding
        role_ref = self.rbac_repo.create_cluster_role_ref(user.restricted_role_name)
        subject = self.rbac_repo.create_service_account_subject(user.name, user.namespace)

        self.rbac_repo.create_or_update_cluster_role_binding(
            name=user.restricted_binding_name,
            role_ref=role_ref,
            subjects=[subject]
        )
        logger.info(f"Created restricted ClusterRoleBinding '{user.restricted_binding_name}'")

        if self.audit:
            self.audit.log_create(
                resource_type="ClusterRole",
                name=user.restricted_role_name,
                details={"user": user.name, "namespaces": namespaces}
            )

    def delete_user_restricted_permissions(self, user: User) -> None:
        """Delete restricted namespace ClusterRole and binding for a user."""
        try:
            self.rbac_repo.delete_cluster_role_binding(user.restricted_binding_name)
            logger.info(f"Deleted restricted ClusterRoleBinding '{user.restricted_binding_name}'")
        except ResourceNotFoundError:
            pass

        try:
            self.rbac_repo.delete_cluster_role(user.restricted_role_name)
            logger.info(f"Deleted restricted ClusterRole '{user.restricted_role_name}'")
        except ResourceNotFoundError:
            pass

    # ==================== Group RBAC ====================

    def create_group_role_bindings(self, group: Group) -> None:
        """Create all role bindings for a group.

        Args:
            group: The Group object
        """
        # Create bindings for namespaced cluster roles
        for cr_binding in group.spec.get_namespaced_roles():
            self._create_group_namespaced_binding(group, cr_binding)

        # Create bindings for cluster-wide cluster roles
        for cr_binding in group.spec.get_cluster_wide_roles():
            self._create_group_cluster_binding(group, cr_binding)

        # Create bindings for roles
        for role_name in group.spec.roles:
            self._create_group_role_binding(group, role_name)

    def _create_group_namespaced_binding(self, group: Group,
                                          cr_binding: CRoleBinding) -> None:
        """Create a RoleBinding for a group's ClusterRole in a namespace."""
        binding_name = group.role_binding_name(
            cr_binding.namespace, cr_binding.cluster_role
        )

        subject = self.rbac_repo.create_group_subject(
            group.name, cr_binding.namespace
        )
        role_ref = self.rbac_repo.create_cluster_role_ref(cr_binding.cluster_role)

        self.rbac_repo.create_or_update_role_binding(
            name=binding_name,
            namespace=cr_binding.namespace,
            role_ref=role_ref,
            subjects=[subject]
        )
        logger.info(f"Created RoleBinding '{binding_name}' for group '{group.name}'")

        if self.audit:
            self.audit.log_create(
                resource_type="RoleBinding",
                name=binding_name,
                namespace=cr_binding.namespace,
                details={"group": group.name, "clusterRole": cr_binding.cluster_role}
            )

    def _create_group_cluster_binding(self, group: Group,
                                       cr_binding: CRoleBinding) -> None:
        """Create a ClusterRoleBinding for a group."""
        binding_name = group.cluster_role_binding_name(cr_binding.cluster_role)

        subject = self.rbac_repo.create_group_subject(group.name)
        role_ref = self.rbac_repo.create_cluster_role_ref(cr_binding.cluster_role)

        self.rbac_repo.create_or_update_cluster_role_binding(
            name=binding_name,
            role_ref=role_ref,
            subjects=[subject]
        )
        logger.info(f"Created ClusterRoleBinding '{binding_name}' for group '{group.name}'")

        if self.audit:
            self.audit.log_create(
                resource_type="ClusterRoleBinding",
                name=binding_name,
                details={"group": group.name, "clusterRole": cr_binding.cluster_role}
            )

    def _create_group_role_binding(self, group: Group, role_name: str) -> None:
        """Create a RoleBinding for a group's Role."""
        binding_name = group.role_binding_name(group.namespace, role_name)

        subject = self.rbac_repo.create_group_subject(group.name)
        role_ref = self.rbac_repo.create_role_ref(role_name)

        self.rbac_repo.create_or_update_role_binding(
            name=binding_name,
            namespace=group.namespace,
            role_ref=role_ref,
            subjects=[subject]
        )
        logger.info(f"Created RoleBinding '{binding_name}' for group '{group.name}'")

        if self.audit:
            self.audit.log_create(
                resource_type="RoleBinding",
                name=binding_name,
                namespace=group.namespace,
                details={"group": group.name, "role": role_name}
            )

    def update_group_role_bindings(self, group: Group) -> None:
        """Update role bindings for a group, removing stale ones."""
        self._cleanup_group_bindings(group)
        self.create_group_role_bindings(group)

    def _cleanup_group_bindings(self, group: Group) -> None:
        """Remove bindings that are no longer in the group spec."""
        # Expected cluster role bindings (cluster-wide)
        expected_crb: Set[str] = set()
        for cr in group.spec.get_cluster_wide_roles():
            expected_crb.add(cr.cluster_role)

        # Expected role bindings (namespaced)
        expected_rb: Set[Tuple[str, str]] = set()
        for cr in group.spec.get_namespaced_roles():
            expected_rb.add((cr.namespace, cr.cluster_role))

        # Clean up ClusterRoleBindings
        crb_bindings = self.rbac_repo.find_cluster_role_bindings_for_subject(
            subject_name=group.name,
            subject_kind="Group"
        )
        for binding in crb_bindings:
            if binding.role_ref.name not in expected_crb:
                self._delete_cluster_role_binding(binding.metadata.name)

        # Clean up RoleBindings
        rb_bindings = self.rbac_repo.find_bindings_for_subject(
            subject_name=group.name,
            subject_kind="Group"
        )
        for binding in rb_bindings:
            ns = binding.metadata.namespace
            role = binding.role_ref.name
            # Only clean up single-subject bindings
            if len(binding.subjects) == 1:
                if binding.role_ref.kind == "ClusterRole":
                    if (ns, role) not in expected_rb:
                        self._delete_role_binding(binding.metadata.name, ns)

    def delete_group_role_bindings(self, group: Group) -> None:
        """Delete all role bindings for a group."""
        # Delete namespaced RoleBindings
        bindings = self.rbac_repo.find_bindings_for_subject(
            subject_name=group.name,
            subject_kind="Group"
        )
        for binding in bindings:
            self._delete_role_binding(
                binding.metadata.name,
                binding.metadata.namespace
            )

        # Delete ClusterRoleBindings
        crb_bindings = self.rbac_repo.find_cluster_role_bindings_for_subject(
            subject_name=group.name,
            subject_kind="Group"
        )
        for binding in crb_bindings:
            self._delete_cluster_role_binding(binding.metadata.name)
