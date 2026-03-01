"""Unit tests for GroupService."""

import pytest
from unittest.mock import MagicMock, patch

from app.services.group_service import GroupService
from app.exceptions import ValidationError


class TestGroupServiceCreate:
    """Tests for GroupService.create_group method."""

    def test_create_group_basic(self, group_service, sample_group_body,
                                 sample_group_spec, mock_audit_logger):
        """Test basic group creation."""
        result = group_service.create_group(
            sample_group_body, sample_group_spec, "default"
        )

        assert result["status"] == "created"
        assert result["bindings"] == 3  # 2 CRoles + 1 Role

    def test_create_group_logs_audit(self, group_service, sample_group_body,
                                      sample_group_spec, mock_audit_logger):
        """Test that audit logging is called."""
        group_service.create_group(
            sample_group_body, sample_group_spec, "default"
        )

        mock_audit_logger.log_create.assert_called()

    def test_create_group_invalid_name_raises_error(self, group_service):
        """Test that invalid group name raises ValidationError."""
        body = {
            "metadata": {"name": "-invalid", "namespace": "default"},
            "spec": {"CRoles": [], "Roles": []}
        }
        spec = {"CRoles": [], "Roles": []}

        with pytest.raises(ValidationError):
            group_service.create_group(body, spec, "default")


class TestGroupServiceUpdate:
    """Tests for GroupService.update_group method."""

    def test_update_group_basic(self, group_service, sample_group_body,
                                 sample_group_spec):
        """Test basic group update."""
        result = group_service.update_group(
            sample_group_body, sample_group_spec, "default"
        )

        assert result["status"] == "updated"

    def test_update_group_updates_bindings(self, group_service, sample_group_body,
                                            sample_group_spec, mock_audit_logger):
        """Test that bindings are updated."""
        result = group_service.update_group(
            sample_group_body, sample_group_spec, "default"
        )

        # Should have correct binding count
        assert result["bindings"] == 3


class TestGroupServiceDelete:
    """Tests for GroupService.delete_group method."""

    def test_delete_group_basic(self, group_service, sample_group_body):
        """Test basic group deletion."""
        with patch('app.services.group_service.client') as mock_client:
            mock_custom_api = MagicMock()
            mock_client.CustomObjectsApi.return_value = mock_custom_api

            result = group_service.delete_group(sample_group_body, "default")

            assert result["status"] == "deleted"

    def test_delete_group_handles_not_found(self, group_service, sample_group_body):
        """Test that 404 on custom resource is handled."""
        with patch('app.services.group_service.client') as mock_client:
            from kubernetes.client.rest import ApiException
            mock_custom_api = MagicMock()
            mock_custom_api.delete_namespaced_custom_object.side_effect = \
                ApiException(status=404)
            mock_client.CustomObjectsApi.return_value = mock_custom_api

            result = group_service.delete_group(sample_group_body, "default")

            assert result["status"] == "deleted"
