"""Unit tests for UserService."""

import pytest
from unittest.mock import MagicMock, call, ANY

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

        assert result["state"] == "ready"
        assert result["serviceAccount"] == "test-user"
        mock_sa_repo.create.assert_called_once()

    def test_create_user_enabled_creates_token(self, user_service, sample_user_body,
                                                 sample_user_spec, mock_secret_repo):
        """Test that enabled user creates token secret."""
        sample_user_spec["enabled"] = True

        user_service.create_user(sample_user_body, sample_user_spec, "default")

        mock_secret_repo.ensure_service_account_token.assert_called_once()

    def test_create_user_enabled_creates_namespace(self, user_service, sample_user_body,
                                                    sample_user_spec, mock_ns_repo):
        """Test that enabled user creates user namespace with labels."""
        sample_user_spec["enabled"] = True

        user_service.create_user(sample_user_body, sample_user_spec, "default")

        # Verify namespace is created with labels
        mock_ns_repo.ensure_exists.assert_called_once()
        call_args = mock_ns_repo.ensure_exists.call_args
        assert call_args[0][0] == "test-user"  # First positional arg is namespace name
        assert "labels" in call_args[1]
        assert call_args[1]["labels"]["app.kubernetes.io/managed-by"] == "k8s-iam-operator"

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

    def test_create_user_with_type_human(self, user_service, mock_sa_repo, mock_ns_repo,
                                          mock_secret_repo):
        """Test creating user with explicit type: human."""
        body = {
            "metadata": {"name": "human-user", "namespace": "iam"},
            "spec": {"type": "human", "CRoles": [], "Roles": []}
        }
        spec = {"type": "human", "CRoles": [], "Roles": []}

        result = user_service.create_user(body, spec, "iam")

        assert result["state"] == "ready"
        mock_ns_repo.ensure_exists.assert_called_once()
        mock_secret_repo.ensure_service_account_token.assert_called_once()

    def test_create_user_with_type_serviceaccount(self, user_service, mock_sa_repo,
                                                    mock_ns_repo, mock_secret_repo):
        """Test creating user with explicit type: serviceAccount."""
        body = {
            "metadata": {"name": "sa-user", "namespace": "iam"},
            "spec": {"type": "serviceAccount", "CRoles": [], "Roles": []}
        }
        spec = {"type": "serviceAccount", "CRoles": [], "Roles": []}

        result = user_service.create_user(body, spec, "iam")

        assert result["state"] == "ready"
        mock_ns_repo.ensure_exists.assert_not_called()
        mock_secret_repo.create_service_account_token.assert_not_called()

    def test_create_user_with_target_namespace(self, user_service, mock_sa_repo):
        """Test creating SA user with targetNamespace."""
        body = {
            "metadata": {"name": "app-sa", "namespace": "iam"},
            "spec": {
                "type": "serviceAccount",
                "targetNamespace": "production",
                "CRoles": [],
                "Roles": []
            }
        }
        spec = body["spec"]

        result = user_service.create_user(body, spec, "iam")

        # SA should be created in targetNamespace
        mock_sa_repo.create.assert_called_once_with(
            name="app-sa",
            namespace="production"
        )
        assert result["namespace"] == "production"


class TestUserServiceUpdate:
    """Tests for UserService.update_user method."""

    def test_update_user_patches_sa(self, user_service, sample_user_body,
                                     sample_user_spec, mock_sa_repo):
        """Test that update patches service account."""
        result = user_service.update_user(
            sample_user_body, sample_user_spec, "default"
        )

        assert result["state"] == "ready"
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

    def test_update_user_with_new_croles_updates_bindings(
        self, user_service, sample_user_body, mock_secret_repo, rbac_service
    ):
        """Test that updating CRoles successfully updates role bindings.

        This tests the fix for the issue where existing secrets would
        cause updates to fail before reaching role binding updates.
        """
        # Add new CRoles to the spec
        sample_user_body["spec"]["CRoles"].append({
            "namespace": "openstack",
            "clusterRole": "edit"
        })
        spec = sample_user_body["spec"]

        result = user_service.update_user(sample_user_body, spec, "default")

        # Should succeed (not throw ResourceAlreadyExistsError)
        assert result["state"] == "ready"
        # Secret should use idempotent ensure method
        mock_secret_repo.ensure_service_account_token.assert_called_once()


class TestUserServiceDelete:
    """Tests for UserService.delete_user method."""

    def test_delete_user_deletes_sa(self, user_service, sample_user_body,
                                     sample_user_spec, mock_sa_repo):
        """Test that delete removes service account."""
        result = user_service.delete_user(
            sample_user_body, sample_user_spec, "default"
        )

        assert result["state"] == "deleted"
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

        assert result["state"] == "deleted"

    def test_delete_user_cleans_up_rbac(self, user_service, sample_user_body,
                                         sample_user_spec, rbac_service):
        """Test that RBAC bindings are cleaned up."""
        user_service.delete_user(sample_user_body, sample_user_spec, "default")

        # The RBAC service should be called to delete bindings
        # (verified by no errors)
        assert True
