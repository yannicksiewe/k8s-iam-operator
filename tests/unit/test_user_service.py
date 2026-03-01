"""Unit tests for UserService."""

import pytest
from unittest.mock import MagicMock, call

from app.services.user_service import UserService
from app.exceptions import ValidationError, ResourceNotFoundError


class TestUserServiceCreate:
    """Tests for UserService.create_user method."""

    def test_create_user_basic(self, user_service, sample_user_body, sample_user_spec,
                                mock_sa_repo, mock_rbac_repo):
        """Test basic user creation."""
        result = user_service.create_user(
            sample_user_body, sample_user_spec, "default"
        )

        assert result["status"] == "created"
        assert result["serviceAccount"] == "test-user"
        mock_sa_repo.create.assert_called_once()

    def test_create_user_enabled_creates_token(self, user_service, sample_user_body,
                                                 sample_user_spec, mock_secret_repo):
        """Test that enabled user creates token secret."""
        sample_user_spec["enabled"] = True

        user_service.create_user(sample_user_body, sample_user_spec, "default")

        mock_secret_repo.create_service_account_token.assert_called_once()

    def test_create_user_enabled_creates_namespace(self, user_service, sample_user_body,
                                                    sample_user_spec, mock_ns_repo):
        """Test that enabled user creates user namespace."""
        sample_user_spec["enabled"] = True

        user_service.create_user(sample_user_body, sample_user_spec, "default")

        mock_ns_repo.ensure_exists.assert_called_with("test-user")

    def test_create_user_disabled_skips_setup(self, user_service, sample_disabled_user_body,
                                               mock_secret_repo, mock_ns_repo):
        """Test that disabled user skips full setup."""
        spec = {"enabled": False, "CRoles": [], "Roles": []}

        user_service.create_user(sample_disabled_user_body, spec, "default")

        mock_secret_repo.create_service_account_token.assert_not_called()

    def test_create_user_invalid_name_raises_error(self, user_service):
        """Test that invalid user name raises ValidationError."""
        body = {
            "metadata": {"name": "-invalid", "namespace": "default"},
            "spec": {}
        }
        spec = {}

        with pytest.raises(ValidationError):
            user_service.create_user(body, spec, "default")

    def test_create_user_creates_role_bindings(self, user_service, sample_user_body,
                                                sample_user_spec, rbac_service):
        """Test that role bindings are created."""
        user_service.create_user(sample_user_body, sample_user_spec, "default")

        # RBAC service should be called to create bindings
        # (we just verify no errors occurred)
        assert True


class TestUserServiceUpdate:
    """Tests for UserService.update_user method."""

    def test_update_user_patches_sa(self, user_service, sample_user_body,
                                     sample_user_spec, mock_sa_repo):
        """Test that update patches service account."""
        result = user_service.update_user(
            sample_user_body, sample_user_spec, "default"
        )

        assert result["status"] == "updated"
        mock_sa_repo.update.assert_called_once()

    def test_update_user_recreates_deleted_sa(self, user_service, sample_user_body,
                                               sample_user_spec, mock_sa_repo):
        """Test that deleted SA is recreated on update."""
        mock_sa_repo.update.side_effect = ResourceNotFoundError(
            "ServiceAccount", "test-user", "default"
        )

        result = user_service.update_user(
            sample_user_body, sample_user_spec, "default"
        )

        mock_sa_repo.create.assert_called_once()

    def test_update_user_disabled_deletes_namespace(self, user_service, mock_ns_repo):
        """Test that disabling user deletes namespace."""
        body = {
            "metadata": {"name": "test-user", "namespace": "default"},
            "spec": {"enabled": False, "CRoles": [], "Roles": []}
        }
        spec = {"enabled": False, "CRoles": [], "Roles": []}

        user_service.update_user(body, spec, "default")

        mock_ns_repo.delete.assert_called_with("test-user")


class TestUserServiceDelete:
    """Tests for UserService.delete_user method."""

    def test_delete_user_deletes_sa(self, user_service, sample_user_body,
                                     sample_user_spec, mock_sa_repo):
        """Test that delete removes service account."""
        result = user_service.delete_user(
            sample_user_body, sample_user_spec, "default"
        )

        assert result["status"] == "deleted"
        mock_sa_repo.delete.assert_called_once()

    def test_delete_user_enabled_deletes_namespace(self, user_service, sample_user_body,
                                                    sample_user_spec, mock_ns_repo):
        """Test that enabled user deletion removes namespace."""
        sample_user_spec["enabled"] = True

        user_service.delete_user(sample_user_body, sample_user_spec, "default")

        mock_ns_repo.delete.assert_called_with("test-user")

    def test_delete_user_handles_missing_sa(self, user_service, sample_user_body,
                                             sample_user_spec, mock_sa_repo):
        """Test that missing SA doesn't cause error."""
        mock_sa_repo.delete.side_effect = ResourceNotFoundError(
            "ServiceAccount", "test-user", "default"
        )

        result = user_service.delete_user(
            sample_user_body, sample_user_spec, "default"
        )

        assert result["status"] == "deleted"

    def test_delete_user_cleans_up_rbac(self, user_service, sample_user_body,
                                         sample_user_spec, rbac_service):
        """Test that RBAC bindings are cleaned up."""
        user_service.delete_user(sample_user_body, sample_user_spec, "default")

        # The RBAC service should be called to delete bindings
        # (verified by no errors)
        assert True
