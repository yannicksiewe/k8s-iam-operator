"""Pytest fixtures for k8s-iam-operator tests."""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from app.models.user import User, UserSpec, ClusterRoleBinding
from app.models.group import Group, GroupSpec
from app.models.role import Role, ClusterRole, RoleSpec, PolicyRule
from app.repositories import (
    NamespaceRepository,
    ServiceAccountRepository,
    SecretRepository,
    RBACRepository,
)
from app.services import (
    UserService,
    GroupService,
    RoleService,
    RBACService,
    KubeconfigService,
)
from app.utils.audit import AuditLogger
from app.container import ServiceContainer


# ==================== Mock Repositories ====================

@pytest.fixture
def mock_ns_repo():
    """Create a mock namespace repository."""
    repo = MagicMock(spec=NamespaceRepository)
    repo.exists.return_value = True
    repo.get.return_value = MagicMock()
    repo.create.return_value = MagicMock()
    repo.ensure_exists.return_value = MagicMock()
    return repo


@pytest.fixture
def mock_sa_repo():
    """Create a mock service account repository."""
    repo = MagicMock(spec=ServiceAccountRepository)
    repo.exists.return_value = True
    repo.get.return_value = MagicMock()
    repo.create.return_value = MagicMock()
    repo.ensure_exists.return_value = MagicMock()
    return repo


@pytest.fixture
def mock_secret_repo():
    """Create a mock secret repository."""
    repo = MagicMock(spec=SecretRepository)
    repo.exists.return_value = True

    # Mock token secret
    mock_token = MagicMock()
    mock_token.data = {"token": "dGVzdC10b2tlbg=="}  # base64 of "test-token"
    repo.get.return_value = mock_token

    # Mock CA configmap
    mock_ca = MagicMock()
    mock_ca.data = {"ca.crt": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----"}
    repo.get_configmap.return_value = mock_ca

    return repo


@pytest.fixture
def mock_rbac_repo():
    """Create a mock RBAC repository."""
    repo = MagicMock(spec=RBACRepository)
    repo.role_exists.return_value = False
    repo.cluster_role_exists.return_value = False
    repo.role_binding_exists.return_value = False
    repo.cluster_role_binding_exists.return_value = False
    repo.find_bindings_for_subject.return_value = []
    repo.find_cluster_role_bindings_for_subject.return_value = []
    repo.list_role_bindings.return_value = []
    repo.list_cluster_role_bindings.return_value = []
    return repo


@pytest.fixture
def mock_audit_logger():
    """Create a mock audit logger."""
    return MagicMock(spec=AuditLogger)


# ==================== Services with Mocked Dependencies ====================

@pytest.fixture
def rbac_service(mock_rbac_repo, mock_ns_repo, mock_audit_logger):
    """Create an RBAC service with mocked repositories."""
    return RBACService(
        rbac_repo=mock_rbac_repo,
        ns_repo=mock_ns_repo,
        audit_logger=mock_audit_logger
    )


@pytest.fixture
def kubeconfig_service(mock_secret_repo, mock_audit_logger):
    """Create a kubeconfig service with mocked repositories."""
    # Mock the api_client
    mock_api_client = MagicMock()
    mock_api_client.configuration.host = "https://kubernetes.default.svc"
    mock_secret_repo.api_client = mock_api_client

    return KubeconfigService(
        secret_repo=mock_secret_repo,
        audit_logger=mock_audit_logger
    )


@pytest.fixture
def user_service(mock_sa_repo, mock_ns_repo, mock_secret_repo,
                 rbac_service, kubeconfig_service, mock_audit_logger):
    """Create a user service with mocked dependencies."""
    return UserService(
        sa_repo=mock_sa_repo,
        ns_repo=mock_ns_repo,
        secret_repo=mock_secret_repo,
        rbac_service=rbac_service,
        kubeconfig_service=kubeconfig_service,
        audit_logger=mock_audit_logger
    )


@pytest.fixture
def group_service(rbac_service, mock_audit_logger):
    """Create a group service with mocked dependencies."""
    return GroupService(
        rbac_service=rbac_service,
        audit_logger=mock_audit_logger
    )


@pytest.fixture
def role_service(mock_rbac_repo, mock_ns_repo, mock_audit_logger):
    """Create a role service with mocked dependencies."""
    return RoleService(
        rbac_repo=mock_rbac_repo,
        ns_repo=mock_ns_repo,
        audit_logger=mock_audit_logger
    )


# ==================== Sample Data ====================

@pytest.fixture
def sample_user_body() -> Dict[str, Any]:
    """Create a sample User CRD body."""
    return {
        "apiVersion": "k8sio.auth/v1",
        "kind": "User",
        "metadata": {
            "name": "test-user",
            "namespace": "default",
            "uid": "test-uid-123",
            "resourceVersion": "12345"
        },
        "spec": {
            "enabled": True,
            "CRoles": [
                {"namespace": "dev", "clusterRole": "view"},
                {"namespace": "staging", "clusterRole": "edit", "group": "devops"}
            ],
            "Roles": ["custom-role"]
        }
    }


@pytest.fixture
def sample_user_spec() -> Dict[str, Any]:
    """Create a sample User spec."""
    return {
        "enabled": True,
        "CRoles": [
            {"namespace": "dev", "clusterRole": "view"},
            {"namespace": "staging", "clusterRole": "edit"}
        ],
        "Roles": ["custom-role"]
    }


@pytest.fixture
def sample_disabled_user_body() -> Dict[str, Any]:
    """Create a sample disabled User CRD body."""
    return {
        "apiVersion": "k8sio.auth/v1",
        "kind": "User",
        "metadata": {
            "name": "disabled-user",
            "namespace": "default"
        },
        "spec": {
            "enabled": False,
            "CRoles": [],
            "Roles": []
        }
    }


@pytest.fixture
def sample_group_body() -> Dict[str, Any]:
    """Create a sample Group CRD body."""
    return {
        "apiVersion": "k8sio.auth/v1",
        "kind": "Group",
        "metadata": {
            "name": "devops",
            "namespace": "default",
            "uid": "group-uid-123"
        },
        "spec": {
            "CRoles": [
                {"namespace": "dev", "clusterRole": "view"},
                {"clusterRole": "cluster-view"}
            ],
            "Roles": ["custom-role"]
        }
    }


@pytest.fixture
def sample_group_spec() -> Dict[str, Any]:
    """Create a sample Group spec."""
    return {
        "CRoles": [
            {"namespace": "dev", "clusterRole": "view"},
            {"clusterRole": "cluster-view"}
        ],
        "Roles": ["custom-role"]
    }


@pytest.fixture
def sample_role_body() -> Dict[str, Any]:
    """Create a sample Role CRD body."""
    return {
        "apiVersion": "k8sio.auth/v1",
        "kind": "Role",
        "metadata": {
            "name": "custom-role",
            "namespace": "default"
        },
        "spec": {
            "rules": [
                {
                    "apiGroups": [""],
                    "resources": ["pods"],
                    "verbs": ["get", "list", "watch"]
                }
            ]
        }
    }


@pytest.fixture
def sample_cluster_role_body() -> Dict[str, Any]:
    """Create a sample ClusterRole CRD body."""
    return {
        "apiVersion": "k8sio.auth/v1",
        "kind": "ClusterRole",
        "metadata": {
            "name": "custom-cluster-role"
        },
        "spec": {
            "rules": [
                {
                    "apiGroups": [""],
                    "resources": ["namespaces"],
                    "verbs": ["get", "list", "watch"]
                }
            ]
        }
    }


@pytest.fixture
def sample_role_spec() -> Dict[str, Any]:
    """Create a sample Role spec."""
    return {
        "rules": [
            {
                "apiGroups": [""],
                "resources": ["pods"],
                "verbs": ["get", "list", "watch"]
            }
        ]
    }


# ==================== Model Fixtures ====================

@pytest.fixture
def sample_user(sample_user_body) -> User:
    """Create a sample User model."""
    return User.from_dict(sample_user_body)


@pytest.fixture
def sample_group(sample_group_body) -> Group:
    """Create a sample Group model."""
    return Group.from_dict(sample_group_body)


@pytest.fixture
def sample_role(sample_role_body) -> Role:
    """Create a sample Role model."""
    return Role.from_dict(sample_role_body)


@pytest.fixture
def sample_cluster_role(sample_cluster_role_body) -> ClusterRole:
    """Create a sample ClusterRole model."""
    return ClusterRole.from_dict(sample_cluster_role_body)


# ==================== Container Reset ====================

@pytest.fixture(autouse=True)
def reset_container():
    """Reset the service container before each test."""
    ServiceContainer.reset()
    yield
    ServiceContainer.reset()
