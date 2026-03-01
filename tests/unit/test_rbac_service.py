"""Unit tests for RBACService."""

import pytest
from unittest.mock import MagicMock, call

from kubernetes import client

from app.services.rbac_service import RBACService
from app.models.user import User, UserSpec, ClusterRoleBinding


class TestRBACServiceUserBindings:
    """Tests for RBACService user binding methods."""

    def test_create_user_role_bindings(self, rbac_service, sample_user,
                                        mock_rbac_repo, mock_ns_repo):
        """Test creating user role bindings."""
        mock_rbac_repo.cluster_role_exists.return_value = True

        rbac_service.create_user_role_bindings(sample_user)

        # Should create bindings for each CRole
        assert mock_rbac_repo.create_or_update_role_binding.call_count >= 1

    def test_create_user_role_bindings_skips_missing_namespace(
        self, rbac_service, sample_user, mock_ns_repo, mock_rbac_repo
    ):
        """Test that missing namespaces are skipped."""
        mock_ns_repo.exists.return_value = False

        rbac_service.create_user_role_bindings(sample_user)

        # Should not create binding for missing namespace
        mock_rbac_repo.create_or_update_role_binding.assert_not_called()

    def test_create_user_role_bindings_skips_missing_role(
        self, rbac_service, sample_user, mock_rbac_repo, mock_ns_repo
    ):
        """Test that missing cluster roles are skipped."""
        mock_ns_repo.exists.return_value = True
        mock_rbac_repo.cluster_role_exists.return_value = False

        rbac_service.create_user_role_bindings(sample_user)

        mock_rbac_repo.create_or_update_role_binding.assert_not_called()

    def test_delete_user_role_bindings(self, rbac_service, sample_user,
                                        mock_rbac_repo):
        """Test deleting user role bindings."""
        # Setup mock bindings to delete
        mock_binding = MagicMock()
        mock_binding.metadata.name = "test-binding"
        mock_binding.metadata.namespace = "default"
        mock_rbac_repo.find_bindings_for_subject.return_value = [mock_binding]
        mock_rbac_repo.find_cluster_role_bindings_for_subject.return_value = []

        rbac_service.delete_user_role_bindings(sample_user)

        mock_rbac_repo.delete_role_binding.assert_called()


class TestRBACServiceRestrictedPermissions:
    """Tests for restricted namespace permissions."""

    def test_create_user_restricted_permissions(self, rbac_service, sample_user,
                                                  mock_rbac_repo):
        """Test creating restricted permissions."""
        rbac_service.create_user_restricted_permissions(sample_user)

        # Should create ClusterRole
        mock_rbac_repo.create_or_update_cluster_role.assert_called_once()

        # Should create ClusterRoleBinding
        mock_rbac_repo.create_or_update_cluster_role_binding.assert_called_once()

    def test_restricted_permissions_includes_user_namespace(
        self, rbac_service, sample_user, mock_rbac_repo
    ):
        """Test that restricted permissions include user namespace."""
        rbac_service.create_user_restricted_permissions(sample_user)

        # Get the rules passed to create_or_update_cluster_role
        call_args = mock_rbac_repo.create_or_update_cluster_role.call_args
        rules = call_args[1]["rules"]

        # Should include user namespace
        resource_names = rules[0]["resourceNames"]
        assert sample_user.user_namespace in resource_names

    def test_delete_user_restricted_permissions(self, rbac_service, sample_user,
                                                  mock_rbac_repo):
        """Test deleting restricted permissions."""
        rbac_service.delete_user_restricted_permissions(sample_user)

        mock_rbac_repo.delete_cluster_role_binding.assert_called_once()
        mock_rbac_repo.delete_cluster_role.assert_called_once()


class TestRBACServiceGroupBindings:
    """Tests for RBACService group binding methods."""

    def test_create_group_role_bindings(self, rbac_service, sample_group,
                                         mock_rbac_repo):
        """Test creating group role bindings."""
        rbac_service.create_group_role_bindings(sample_group)

        # Should create bindings for namespaced and cluster-wide roles
        assert mock_rbac_repo.create_or_update_role_binding.call_count >= 1

    def test_create_group_cluster_binding(self, rbac_service, sample_group,
                                           mock_rbac_repo):
        """Test creating cluster-wide group binding."""
        rbac_service.create_group_role_bindings(sample_group)

        # Should create ClusterRoleBinding for cluster-wide role
        mock_rbac_repo.create_or_update_cluster_role_binding.assert_called()

    def test_delete_group_role_bindings(self, rbac_service, sample_group,
                                         mock_rbac_repo):
        """Test deleting group role bindings."""
        mock_rbac_repo.find_bindings_for_subject.return_value = []
        mock_rbac_repo.find_cluster_role_bindings_for_subject.return_value = []

        rbac_service.delete_group_role_bindings(sample_group)

        # Methods should be called even if no bindings found
        mock_rbac_repo.find_bindings_for_subject.assert_called()
        mock_rbac_repo.find_cluster_role_bindings_for_subject.assert_called()


class TestRBACServiceCleanup:
    """Tests for RBAC cleanup operations."""

    def test_cleanup_stale_bindings(self, rbac_service, mock_rbac_repo):
        """Test cleanup of stale bindings."""
        # Create a user with reduced bindings
        user_body = {
            "metadata": {"name": "test-user", "namespace": "default"},
            "spec": {
                "enabled": False,
                "CRoles": [{"namespace": "dev", "clusterRole": "view"}],
                "Roles": []
            }
        }
        user = User.from_dict(user_body)

        # Mock existing binding that should be removed
        mock_binding = MagicMock()
        mock_binding.metadata.name = "old-binding"
        mock_binding.metadata.namespace = "staging"
        mock_binding.role_ref.name = "edit"
        mock_binding.role_ref.kind = "ClusterRole"
        mock_binding.subjects = [MagicMock()]
        mock_rbac_repo.find_bindings_for_subject.return_value = [mock_binding]

        rbac_service._cleanup_user_bindings(user)

        # Old binding should be deleted
        mock_rbac_repo.delete_role_binding.assert_called_once_with(
            "old-binding", "staging"
        )
