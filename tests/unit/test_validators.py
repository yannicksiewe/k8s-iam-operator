"""Unit tests for validators module."""

import pytest

from app.validators import (
    validate_dns_label,
    validate_kubernetes_name,
    validate_namespace,
    validate_user_name,
    validate_group_name,
    validate_role_name,
    validate_croles_spec,
    validate_roles_spec,
    validate_rbac_rule,
    validate_user_spec,
    validate_group_spec,
    VALID_VERBS,
    RESERVED_NAMESPACES,
)
from app.exceptions import ValidationError


class TestValidateDnsLabel:
    """Tests for validate_dns_label function."""

    def test_valid_simple_name(self):
        """Test valid simple DNS label."""
        assert validate_dns_label("my-service") == "my-service"

    def test_valid_with_numbers(self):
        """Test valid DNS label with numbers."""
        assert validate_dns_label("app-v2") == "app-v2"

    def test_converts_to_lowercase(self):
        """Test that uppercase is converted to lowercase."""
        assert validate_dns_label("MyService") == "myservice"

    def test_empty_string_raises_error(self):
        """Test that empty string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_dns_label("")
        assert "cannot be empty" in exc_info.value.message

    def test_too_long_raises_error(self):
        """Test that string over 63 chars raises error."""
        long_name = "a" * 64
        with pytest.raises(ValidationError) as exc_info:
            validate_dns_label(long_name)
        assert "at most 63 characters" in exc_info.value.message

    def test_invalid_start_char_raises_error(self):
        """Test that starting with dash raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_dns_label("-invalid")
        assert "start with an alphanumeric" in exc_info.value.message

    def test_invalid_end_char_raises_error(self):
        """Test that ending with dash raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_dns_label("invalid-")
        assert "end with an alphanumeric" in exc_info.value.message

    def test_invalid_chars_raises_error(self):
        """Test that special characters raise error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_dns_label("invalid_name")
        assert "lowercase alphanumeric" in exc_info.value.message


class TestValidateNamespace:
    """Tests for validate_namespace function."""

    def test_valid_namespace(self):
        """Test valid namespace name."""
        assert validate_namespace("my-namespace") == "my-namespace"

    def test_reserved_namespace_raises_error(self):
        """Test that reserved namespaces raise error when not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            validate_namespace("kube-system")
        assert "reserved namespace" in exc_info.value.message

    def test_reserved_namespace_allowed_when_flag_set(self):
        """Test that reserved namespaces work with allow_reserved=True."""
        assert validate_namespace("kube-system", allow_reserved=True) == "kube-system"

    def test_all_reserved_namespaces(self):
        """Test all reserved namespaces."""
        for ns in RESERVED_NAMESPACES:
            with pytest.raises(ValidationError):
                validate_namespace(ns, allow_reserved=False)


class TestValidateUserName:
    """Tests for validate_user_name function."""

    def test_valid_user_name(self):
        """Test valid user name."""
        assert validate_user_name("john-doe") == "john-doe"

    def test_invalid_user_name(self):
        """Test invalid user name."""
        with pytest.raises(ValidationError) as exc_info:
            validate_user_name("John.Doe")
        assert exc_info.value.field == "user_name"


class TestValidateCrolesSpec:
    """Tests for validate_croles_spec function."""

    def test_valid_croles(self):
        """Test valid CRoles spec."""
        croles = [
            {"namespace": "dev", "clusterRole": "view"},
            {"clusterRole": "cluster-admin"}
        ]
        result = validate_croles_spec(croles)
        assert len(result) == 2
        assert result[0]["namespace"] == "dev"
        assert result[0]["clusterRole"] == "view"

    def test_empty_croles(self):
        """Test empty CRoles list."""
        assert validate_croles_spec([]) == []

    def test_invalid_not_a_list(self):
        """Test that non-list raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_croles_spec("not a list")
        assert "must be a list" in exc_info.value.message

    def test_missing_cluster_role(self):
        """Test that missing clusterRole raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_croles_spec([{"namespace": "dev"}])
        assert "clusterRole is required" in exc_info.value.message

    def test_duplicate_binding_raises_error(self):
        """Test that duplicate bindings raise error."""
        croles = [
            {"namespace": "dev", "clusterRole": "view"},
            {"namespace": "dev", "clusterRole": "view"}
        ]
        with pytest.raises(ValidationError) as exc_info:
            validate_croles_spec(croles)
        assert "Duplicate" in exc_info.value.message

    def test_with_group(self):
        """Test CRole with group."""
        croles = [{"namespace": "dev", "clusterRole": "view", "group": "devops"}]
        result = validate_croles_spec(croles)
        assert result[0]["group"] == "devops"


class TestValidateRolesSpec:
    """Tests for validate_roles_spec function."""

    def test_valid_roles(self):
        """Test valid Roles spec."""
        roles = ["role1", "role2"]
        result = validate_roles_spec(roles)
        assert result == ["role1", "role2"]

    def test_empty_roles(self):
        """Test empty Roles list."""
        assert validate_roles_spec([]) == []

    def test_invalid_not_a_list(self):
        """Test that non-list raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_roles_spec("not a list")
        assert "must be a list" in exc_info.value.message

    def test_duplicate_roles_raises_error(self):
        """Test that duplicate roles raise error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_roles_spec(["role1", "role1"])
        assert "Duplicate" in exc_info.value.message

    def test_invalid_role_type(self):
        """Test that non-string role raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_roles_spec([123])
        assert "must be a string" in exc_info.value.message


class TestValidateRbacRule:
    """Tests for validate_rbac_rule function."""

    def test_valid_rule(self):
        """Test valid RBAC rule."""
        rule = {
            "apiGroups": [""],
            "resources": ["pods"],
            "verbs": ["get", "list"]
        }
        result = validate_rbac_rule(rule)
        assert result["apiGroups"] == [""]
        assert result["resources"] == ["pods"]
        assert result["verbs"] == ["get", "list"]

    def test_empty_resources_raises_error(self):
        """Test that empty resources raises error."""
        rule = {
            "apiGroups": [""],
            "resources": [],
            "verbs": ["get"]
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_rbac_rule(rule)
        assert "cannot be empty" in exc_info.value.message

    def test_empty_verbs_raises_error(self):
        """Test that empty verbs raises error."""
        rule = {
            "apiGroups": [""],
            "resources": ["pods"],
            "verbs": []
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_rbac_rule(rule)
        assert "cannot be empty" in exc_info.value.message

    def test_invalid_verb_raises_error(self):
        """Test that invalid verb raises error."""
        rule = {
            "apiGroups": [""],
            "resources": ["pods"],
            "verbs": ["invalid-verb"]
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_rbac_rule(rule)
        assert "Invalid verb" in exc_info.value.message

    def test_with_resource_names(self):
        """Test rule with resourceNames."""
        rule = {
            "apiGroups": [""],
            "resources": ["pods"],
            "verbs": ["get"],
            "resourceNames": ["pod1", "pod2"]
        }
        result = validate_rbac_rule(rule)
        assert result["resourceNames"] == ["pod1", "pod2"]


class TestValidateUserSpec:
    """Tests for validate_user_spec function."""

    def test_valid_user_spec(self):
        """Test valid user spec."""
        spec = {
            "enabled": True,
            "CRoles": [{"namespace": "dev", "clusterRole": "view"}],
            "Roles": ["role1"]
        }
        result = validate_user_spec(spec)
        assert result["enabled"] is True
        assert len(result["CRoles"]) == 1
        assert len(result["Roles"]) == 1

    def test_defaults(self):
        """Test spec with minimal fields."""
        spec = {}
        result = validate_user_spec(spec)
        assert result["enabled"] is False
        assert result["CRoles"] == []
        assert result["Roles"] == []

    def test_invalid_enabled_type(self):
        """Test that non-boolean enabled raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_user_spec({"enabled": "yes"})
        assert "must be a boolean" in exc_info.value.message


class TestValidateGroupSpec:
    """Tests for validate_group_spec function."""

    def test_valid_group_spec(self):
        """Test valid group spec."""
        spec = {
            "CRoles": [{"clusterRole": "view"}],
            "Roles": ["role1"]
        }
        result = validate_group_spec(spec)
        assert len(result["CRoles"]) == 1
        assert len(result["Roles"]) == 1

    def test_defaults(self):
        """Test spec with minimal fields."""
        spec = {}
        result = validate_group_spec(spec)
        assert result["CRoles"] == []
        assert result["Roles"] == []
