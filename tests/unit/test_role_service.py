"""Unit tests for RoleService."""

import pytest
from unittest.mock import MagicMock

from app.services.role_service import RoleService
from app.exceptions import ValidationError, ResourceNotFoundError


class TestRoleServiceCreate:
    """Tests for RoleService.create_role method."""

    def test_create_role_new(self, role_service, sample_role_body,
                              sample_role_spec, mock_rbac_repo):
        """Test creating a new Role."""
        mock_rbac_repo.role_exists.return_value = False

        result = role_service.create_role(
            sample_role_body, sample_role_spec, "default"
        )

        assert result["status"] == "created"
        assert result["role"] == "custom-role"
        mock_rbac_repo.create_role.assert_called_once()

    def test_create_role_updates_existing(self, role_service, sample_role_body,
                                           sample_role_spec, mock_rbac_repo):
        """Test updating an existing Role."""
        mock_rbac_repo.role_exists.return_value = True

        result = role_service.create_role(
            sample_role_body, sample_role_spec, "default"
        )

        assert result["status"] == "updated"
        mock_rbac_repo.update_role.assert_called_once()

    def test_create_cluster_role_new(self, role_service, sample_cluster_role_body,
                                      sample_role_spec, mock_rbac_repo):
        """Test creating a new ClusterRole."""
        mock_rbac_repo.cluster_role_exists.return_value = False

        result = role_service.create_role(
            sample_cluster_role_body, sample_role_spec, "default"
        )

        assert result["status"] == "created"
        assert result["clusterRole"] == "custom-cluster-role"
        mock_rbac_repo.create_cluster_role.assert_called_once()

    def test_create_role_waits_for_namespace(self, role_service, sample_role_body,
                                              sample_role_spec, mock_ns_repo,
                                              mock_rbac_repo):
        """Test that Role creation waits for namespace."""
        mock_ns_repo.exists.return_value = True
        mock_rbac_repo.role_exists.return_value = False

        result = role_service.create_role(
            sample_role_body, sample_role_spec, "default"
        )

        mock_ns_repo.exists.assert_called_with("default")
        assert result["status"] == "created"

    def test_create_role_fails_without_namespace(self, role_service, sample_role_body,
                                                  sample_role_spec, mock_ns_repo):
        """Test that Role creation fails if namespace doesn't exist."""
        mock_ns_repo.exists.return_value = False
        role_service.MAX_RETRIES = 0  # Skip retries for test

        result = role_service.create_role(
            sample_role_body, sample_role_spec, "missing-ns"
        )

        assert result["status"] == "error"

    def test_create_role_invalid_spec_raises_error(self, role_service):
        """Test that invalid spec raises ValidationError."""
        body = {
            "kind": "Role",
            "metadata": {"name": "test-role", "namespace": "default"},
            "spec": {"rules": [{"apiGroups": [], "resources": [], "verbs": []}]}
        }
        spec = {"rules": [{"apiGroups": [], "resources": [], "verbs": []}]}

        with pytest.raises(ValidationError):
            role_service.create_role(body, spec, "default")


class TestRoleServiceDelete:
    """Tests for RoleService.delete_role method."""

    def test_delete_role(self, role_service, sample_role_body, mock_rbac_repo):
        """Test deleting a Role."""
        result = role_service.delete_role(sample_role_body, "default")

        assert result["status"] == "deleted"
        mock_rbac_repo.delete_role.assert_called_once_with(
            "custom-role", "default"
        )

    def test_delete_cluster_role(self, role_service, sample_cluster_role_body,
                                  mock_rbac_repo):
        """Test deleting a ClusterRole."""
        result = role_service.delete_role(sample_cluster_role_body, "default")

        assert result["status"] == "deleted"
        mock_rbac_repo.delete_cluster_role.assert_called_once_with(
            "custom-cluster-role"
        )

    def test_delete_role_handles_not_found(self, role_service, sample_role_body,
                                            mock_rbac_repo):
        """Test that 404 is handled gracefully."""
        mock_rbac_repo.delete_role.side_effect = ResourceNotFoundError(
            "Role", "custom-role", "default"
        )

        result = role_service.delete_role(sample_role_body, "default")

        assert result["status"] == "already_deleted"

    def test_delete_cluster_role_handles_not_found(self, role_service,
                                                    sample_cluster_role_body,
                                                    mock_rbac_repo):
        """Test that 404 for ClusterRole is handled."""
        mock_rbac_repo.delete_cluster_role.side_effect = ResourceNotFoundError(
            "ClusterRole", "custom-cluster-role"
        )

        result = role_service.delete_role(sample_cluster_role_body, "default")

        assert result["status"] == "already_deleted"
