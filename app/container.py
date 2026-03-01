"""Dependency injection container for k8s-iam-operator.

This module provides a simple service container that wires up all
dependencies for the operator services.
"""

from typing import Optional

from app.repositories import (
    NamespaceRepository,
    ServiceAccountRepository,
    SecretRepository,
    RBACRepository,
)
from app.repositories.resource_quota_repository import ResourceQuotaRepository
from app.repositories.network_policy_repository import NetworkPolicyRepository
from app.services import (
    UserService,
    GroupService,
    RoleService,
    RBACService,
    KubeconfigService,
)
from app.utils.audit import AuditLogger, get_audit_logger


class ServiceContainer:
    """Container for service dependencies.

    Provides lazy initialization and caching of service instances.
    """

    _instance: Optional["ServiceContainer"] = None

    def __init__(self, audit_enabled: bool = True):
        """Initialize the container.

        Args:
            audit_enabled: Whether to enable audit logging
        """
        self._audit_enabled = audit_enabled
        self._audit_logger: Optional[AuditLogger] = None

        # Repositories
        self._ns_repo: Optional[NamespaceRepository] = None
        self._sa_repo: Optional[ServiceAccountRepository] = None
        self._secret_repo: Optional[SecretRepository] = None
        self._rbac_repo: Optional[RBACRepository] = None
        self._quota_repo: Optional[ResourceQuotaRepository] = None
        self._network_policy_repo: Optional[NetworkPolicyRepository] = None

        # Services
        self._rbac_service: Optional[RBACService] = None
        self._kubeconfig_service: Optional[KubeconfigService] = None
        self._user_service: Optional[UserService] = None
        self._group_service: Optional[GroupService] = None
        self._role_service: Optional[RoleService] = None

    @classmethod
    def get_instance(cls, audit_enabled: bool = True) -> "ServiceContainer":
        """Get or create the singleton container instance.

        Args:
            audit_enabled: Whether to enable audit logging

        Returns:
            The ServiceContainer instance
        """
        if cls._instance is None:
            cls._instance = cls(audit_enabled=audit_enabled)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    # ==================== Audit Logger ====================

    @property
    def audit_logger(self) -> Optional[AuditLogger]:
        """Get the audit logger if enabled."""
        if not self._audit_enabled:
            return None
        if self._audit_logger is None:
            self._audit_logger = get_audit_logger()
        return self._audit_logger

    # ==================== Repositories ====================

    @property
    def namespace_repo(self) -> NamespaceRepository:
        """Get the namespace repository."""
        if self._ns_repo is None:
            self._ns_repo = NamespaceRepository()
        return self._ns_repo

    @property
    def serviceaccount_repo(self) -> ServiceAccountRepository:
        """Get the service account repository."""
        if self._sa_repo is None:
            self._sa_repo = ServiceAccountRepository()
        return self._sa_repo

    @property
    def secret_repo(self) -> SecretRepository:
        """Get the secret repository."""
        if self._secret_repo is None:
            self._secret_repo = SecretRepository()
        return self._secret_repo

    @property
    def rbac_repo(self) -> RBACRepository:
        """Get the RBAC repository."""
        if self._rbac_repo is None:
            self._rbac_repo = RBACRepository()
        return self._rbac_repo

    @property
    def resource_quota_repo(self) -> ResourceQuotaRepository:
        """Get the resource quota repository."""
        if self._quota_repo is None:
            self._quota_repo = ResourceQuotaRepository()
        return self._quota_repo

    @property
    def network_policy_repo(self) -> NetworkPolicyRepository:
        """Get the network policy repository."""
        if self._network_policy_repo is None:
            self._network_policy_repo = NetworkPolicyRepository()
        return self._network_policy_repo

    # ==================== Services ====================

    @property
    def rbac_service(self) -> RBACService:
        """Get the RBAC service."""
        if self._rbac_service is None:
            self._rbac_service = RBACService(
                rbac_repo=self.rbac_repo,
                ns_repo=self.namespace_repo,
                audit_logger=self.audit_logger
            )
        return self._rbac_service

    @property
    def kubeconfig_service(self) -> KubeconfigService:
        """Get the kubeconfig service."""
        if self._kubeconfig_service is None:
            self._kubeconfig_service = KubeconfigService(
                secret_repo=self.secret_repo,
                audit_logger=self.audit_logger
            )
        return self._kubeconfig_service

    @property
    def user_service(self) -> UserService:
        """Get the user service."""
        if self._user_service is None:
            self._user_service = UserService(
                sa_repo=self.serviceaccount_repo,
                ns_repo=self.namespace_repo,
                secret_repo=self.secret_repo,
                rbac_service=self.rbac_service,
                kubeconfig_service=self.kubeconfig_service,
                quota_repo=self.resource_quota_repo,
                network_policy_repo=self.network_policy_repo,
                audit_logger=self.audit_logger
            )
        return self._user_service

    @property
    def group_service(self) -> GroupService:
        """Get the group service."""
        if self._group_service is None:
            self._group_service = GroupService(
                rbac_service=self.rbac_service,
                audit_logger=self.audit_logger
            )
        return self._group_service

    @property
    def role_service(self) -> RoleService:
        """Get the role service."""
        if self._role_service is None:
            self._role_service = RoleService(
                rbac_repo=self.rbac_repo,
                ns_repo=self.namespace_repo,
                audit_logger=self.audit_logger
            )
        return self._role_service


# Global container access function
def get_container() -> ServiceContainer:
    """Get the global service container instance.

    Returns:
        The ServiceContainer instance
    """
    return ServiceContainer.get_instance()
