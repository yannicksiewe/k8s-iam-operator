"""Unit tests for KubeconfigService."""

import pytest
import json
import base64
from unittest.mock import MagicMock

from app.services.kubeconfig_service import KubeconfigService
from app.models.user import User
from app.exceptions import KubeconfigGenerationError, ResourceNotFoundError


class TestKubeconfigServiceGenerate:
    """Tests for kubeconfig generation."""

    def test_generate_kubeconfig_structure(self, kubeconfig_service, sample_user):
        """Test that generated kubeconfig has correct structure."""
        kubeconfig_str = kubeconfig_service.generate_kubeconfig(sample_user)
        kubeconfig = json.loads(kubeconfig_str)

        assert kubeconfig["apiVersion"] == "v1"
        assert kubeconfig["kind"] == "Config"
        assert len(kubeconfig["clusters"]) == 1
        assert len(kubeconfig["contexts"]) == 1
        assert len(kubeconfig["users"]) == 1

    def test_generate_kubeconfig_context_name(self, kubeconfig_service, sample_user):
        """Test that context name is correct."""
        kubeconfig_str = kubeconfig_service.generate_kubeconfig(sample_user)
        kubeconfig = json.loads(kubeconfig_str)

        assert kubeconfig["current-context"] == "test-user-context"
        assert kubeconfig["contexts"][0]["name"] == "test-user-context"

    def test_generate_kubeconfig_user_token(self, kubeconfig_service, sample_user):
        """Test that user token is included."""
        kubeconfig_str = kubeconfig_service.generate_kubeconfig(sample_user)
        kubeconfig = json.loads(kubeconfig_str)

        user_config = kubeconfig["users"][0]
        assert user_config["name"] == "test-user"
        assert "token" in user_config["user"]

    def test_generate_kubeconfig_missing_token_raises_error(
        self, kubeconfig_service, sample_user, mock_secret_repo
    ):
        """Test that missing token raises error."""
        mock_token = MagicMock()
        mock_token.data = {}  # No token
        mock_secret_repo.get.return_value = mock_token

        with pytest.raises(KubeconfigGenerationError) as exc_info:
            kubeconfig_service.generate_kubeconfig(sample_user)

        assert "no token data" in exc_info.value.message

    def test_generate_kubeconfig_missing_ca_raises_error(
        self, kubeconfig_service, sample_user, mock_secret_repo
    ):
        """Test that missing CA raises error."""
        mock_ca = MagicMock()
        mock_ca.data = {}  # No ca.crt
        mock_secret_repo.get_configmap.return_value = mock_ca

        with pytest.raises(KubeconfigGenerationError) as exc_info:
            kubeconfig_service.generate_kubeconfig(sample_user)

        assert "CA certificate" in exc_info.value.message


class TestKubeconfigServiceCreate:
    """Tests for kubeconfig secret creation."""

    def test_create_kubeconfig_secret(self, kubeconfig_service, sample_user,
                                       mock_secret_repo, mock_audit_logger):
        """Test creating kubeconfig secret."""
        kubeconfig_service.create_kubeconfig_secret(sample_user)

        mock_secret_repo.ensure_kubeconfig_secret.assert_called_once()
        call_args = mock_secret_repo.ensure_kubeconfig_secret.call_args

        assert call_args[1]["name"] == "test-user-cluster-config"
        assert call_args[1]["namespace"] == "test-user"

    def test_create_kubeconfig_secret_logs_audit(self, kubeconfig_service, sample_user,
                                                   mock_audit_logger):
        """Test that audit is logged."""
        kubeconfig_service.create_kubeconfig_secret(sample_user)

        mock_audit_logger.log_create.assert_called_once()


class TestKubeconfigServiceDelete:
    """Tests for kubeconfig secret deletion."""

    def test_delete_kubeconfig_secret(self, kubeconfig_service, sample_user,
                                       mock_secret_repo, mock_audit_logger):
        """Test deleting kubeconfig secret."""
        kubeconfig_service.delete_kubeconfig_secret(sample_user)

        mock_secret_repo.delete.assert_called_once_with(
            name="test-user-cluster-config",
            namespace="test-user"
        )
        mock_audit_logger.log_delete.assert_called_once()

    def test_delete_kubeconfig_secret_handles_not_found(
        self, kubeconfig_service, sample_user, mock_secret_repo
    ):
        """Test that missing secret is handled gracefully."""
        mock_secret_repo.delete.side_effect = ResourceNotFoundError(
            "Secret", "test-user-cluster-config", "test-user"
        )

        # Should not raise
        kubeconfig_service.delete_kubeconfig_secret(sample_user)


class TestKubeconfigServiceExists:
    """Tests for kubeconfig existence check."""

    def test_kubeconfig_exists_true(self, kubeconfig_service, sample_user,
                                     mock_secret_repo):
        """Test existence check when secret exists."""
        mock_secret_repo.exists.return_value = True

        assert kubeconfig_service.kubeconfig_exists(sample_user) is True

    def test_kubeconfig_exists_false(self, kubeconfig_service, sample_user,
                                      mock_secret_repo):
        """Test existence check when secret doesn't exist."""
        mock_secret_repo.exists.return_value = False

        assert kubeconfig_service.kubeconfig_exists(sample_user) is False
