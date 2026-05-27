"""Unit tests for model classes."""

import pytest

from app.models.user import User, UserSpec, ClusterRoleBinding, UserType
from app.models.group import Group, GroupSpec
from app.models.role import Role, ClusterRole, RoleSpec, PolicyRule


class TestClusterRoleBinding:
    """Tests for ClusterRoleBinding model."""

    def test_from_dict_basic(self):
        """Test creating from dict with basic fields."""
        data = {"clusterRole": "view", "namespace": "dev"}
        crb = ClusterRoleBinding.from_dict(data)
        assert crb.cluster_role == "view"
        assert crb.namespace == "dev"
        assert crb.group is None

    def test_from_dict_with_group(self):
        """Test creating from dict with group."""
        data = {"clusterRole": "edit", "namespace": "staging", "group": "devops"}
        crb = ClusterRoleBinding.from_dict(data)
        assert crb.cluster_role == "edit"
        assert crb.group == "devops"

    def test_to_dict(self):
        """Test converting to dict."""
        crb = ClusterRoleBinding(cluster_role="view", namespace="dev", group="devs")
        result = crb.to_dict()
        assert result == {"clusterRole": "view", "namespace": "dev", "group": "devs"}

    def test_to_dict_minimal(self):
        """Test converting to dict with minimal fields."""
        crb = ClusterRoleBinding(cluster_role="admin")
        result = crb.to_dict()
        assert result == {"clusterRole": "admin"}

    def test_binding_name_with_namespace(self):
        """Test binding name generation with namespace."""
        crb = ClusterRoleBinding(cluster_role="view", namespace="dev")
        assert crb.binding_name("user1") == "user1-dev-view"

    def test_binding_name_without_namespace(self):
        """Test binding name generation without namespace."""
        crb = ClusterRoleBinding(cluster_role="view")
        assert crb.binding_name("user1") == "user1-view"


class TestUserSpec:
    """Tests for UserSpec model."""

    def test_from_dict_full(self):
        """Test creating from full dict."""
        data = {
            "enabled": True,
            "CRoles": [
                {"namespace": "dev", "clusterRole": "view"},
                {"clusterRole": "cluster-admin"}
            ],
            "Roles": ["role1", "role2"]
        }
        spec = UserSpec.from_dict(data)
        assert spec.enabled is True
        assert len(spec.cluster_roles) == 2
        assert len(spec.roles) == 2

    def test_from_dict_defaults(self):
        """Test defaults for empty dict."""
        spec = UserSpec.from_dict({})
        assert spec.enabled is False
        assert spec.cluster_roles == []
        assert spec.roles == []

    def test_to_dict(self):
        """Test converting to dict."""
        spec = UserSpec(
            enabled=True,
            cluster_roles=[ClusterRoleBinding(cluster_role="view", namespace="dev")],
            roles=["role1"]
        )
        result = spec.to_dict()
        assert result["enabled"] is True
        assert len(result["CRoles"]) == 1
        assert result["Roles"] == ["role1"]

    def test_get_namespaces(self):
        """Test getting namespaces from cluster roles."""
        spec = UserSpec(
            cluster_roles=[
                ClusterRoleBinding(cluster_role="view", namespace="dev"),
                ClusterRoleBinding(cluster_role="edit", namespace="staging"),
                ClusterRoleBinding(cluster_role="admin")  # No namespace
            ]
        )
        namespaces = spec.get_namespaces()
        assert set(namespaces) == {"dev", "staging"}

    def test_from_dict_oidc(self):
        """Test parsing an OIDC user spec."""
        spec = UserSpec.from_dict({
            "type": "oidc",
            "oidcUser": "carol@example.com",
            "CRoles": [{"namespace": "dev", "clusterRole": "edit"}],
        })
        assert spec.user_type == UserType.OIDC
        assert spec.is_oidc is True
        assert spec.is_human is False
        assert spec.is_service_account is False
        assert spec.needs_namespace is True
        assert spec.oidc_user == "carol@example.com"

    def test_to_dict_oidc_includes_oidc_user(self):
        """Test that oidcUser round-trips through to_dict."""
        spec = UserSpec(user_type=UserType.OIDC, oidc_user="carol@example.com")
        result = spec.to_dict()
        assert result["type"] == "oidc"
        assert result["oidcUser"] == "carol@example.com"

    def test_types_are_mutually_exclusive(self):
        """A serviceAccount user is neither human nor oidc."""
        sa = UserSpec.from_dict({"type": "serviceAccount"})
        assert (sa.is_service_account, sa.is_human, sa.is_oidc) == (True, False, False)


class TestUserOIDCSubject:
    """Tests for the RBAC subject helpers on the User model."""

    def _user(self, spec_data):
        return User.from_dict({
            "metadata": {"name": "carol", "namespace": "iam"},
            "spec": spec_data,
        })

    def test_oidc_user_binds_to_user_subject(self):
        user = self._user({"type": "oidc", "oidcUser": "carol@example.com"})
        assert user.rbac_subject_kind == "User"
        assert user.rbac_subject_name == "carol@example.com"

    def test_human_user_binds_to_service_account_subject(self):
        user = self._user({"type": "human"})
        assert user.rbac_subject_kind == "ServiceAccount"
        assert user.rbac_subject_name == "carol"


class TestUser:
    """Tests for User model."""

    def test_from_dict(self, sample_user_body):
        """Test creating User from dict."""
        user = User.from_dict(sample_user_body)
        assert user.name == "test-user"
        assert user.namespace == "default"
        assert user.uid == "test-uid-123"
        assert user.spec.enabled is True
        assert len(user.spec.cluster_roles) == 2

    def test_to_dict(self, sample_user):
        """Test converting User to dict."""
        result = sample_user.to_dict()
        assert result["kind"] == "User"
        assert result["metadata"]["name"] == "test-user"
        assert result["spec"]["enabled"] is True

    def test_property_service_account_name(self, sample_user):
        """Test service_account_name property."""
        assert sample_user.service_account_name == "test-user"

    def test_property_token_secret_name(self, sample_user):
        """Test token_secret_name property."""
        assert sample_user.token_secret_name == "test-user-token"

    def test_property_kubeconfig_secret_name(self, sample_user):
        """Test kubeconfig_secret_name property."""
        assert sample_user.kubeconfig_secret_name == "test-user-cluster-config"

    def test_property_restricted_role_name(self, sample_user):
        """Test restricted_role_name property."""
        assert sample_user.restricted_role_name == "test-user-restricted-namespace-role"

    def test_property_user_namespace(self, sample_user):
        """Test user_namespace property."""
        assert sample_user.user_namespace == "test-user"


class TestGroupSpec:
    """Tests for GroupSpec model."""

    def test_from_dict(self):
        """Test creating from dict."""
        data = {
            "CRoles": [
                {"namespace": "dev", "clusterRole": "view"},
                {"clusterRole": "cluster-view"}
            ],
            "Roles": ["role1"]
        }
        spec = GroupSpec.from_dict(data)
        assert len(spec.cluster_roles) == 2
        assert len(spec.roles) == 1

    def test_get_cluster_wide_roles(self):
        """Test getting cluster-wide roles."""
        spec = GroupSpec.from_dict({
            "CRoles": [
                {"namespace": "dev", "clusterRole": "view"},
                {"clusterRole": "cluster-admin"}
            ]
        })
        cluster_wide = spec.get_cluster_wide_roles()
        assert len(cluster_wide) == 1
        assert cluster_wide[0].cluster_role == "cluster-admin"

    def test_get_namespaced_roles(self):
        """Test getting namespaced roles."""
        spec = GroupSpec.from_dict({
            "CRoles": [
                {"namespace": "dev", "clusterRole": "view"},
                {"clusterRole": "cluster-admin"}
            ]
        })
        namespaced = spec.get_namespaced_roles()
        assert len(namespaced) == 1
        assert namespaced[0].namespace == "dev"


class TestGroup:
    """Tests for Group model."""

    def test_from_dict(self, sample_group_body):
        """Test creating Group from dict."""
        group = Group.from_dict(sample_group_body)
        assert group.name == "devops"
        assert group.namespace == "default"
        assert len(group.spec.cluster_roles) == 2

    def test_role_binding_name(self, sample_group):
        """Test role_binding_name method."""
        assert sample_group.role_binding_name("dev", "view") == "devops-dev-view"

    def test_cluster_role_binding_name(self, sample_group):
        """Test cluster_role_binding_name method."""
        assert sample_group.cluster_role_binding_name("admin") == "devops-default-admin"


class TestPolicyRule:
    """Tests for PolicyRule model."""

    def test_from_dict(self):
        """Test creating from dict."""
        data = {
            "apiGroups": [""],
            "resources": ["pods"],
            "verbs": ["get", "list"],
            "resourceNames": ["pod1"]
        }
        rule = PolicyRule.from_dict(data)
        assert rule.api_groups == [""]
        assert rule.resources == ["pods"]
        assert rule.verbs == ["get", "list"]
        assert rule.resource_names == ["pod1"]

    def test_to_dict(self):
        """Test converting to dict."""
        rule = PolicyRule(
            api_groups=["apps"],
            resources=["deployments"],
            verbs=["create", "delete"]
        )
        result = rule.to_dict()
        assert result["apiGroups"] == ["apps"]
        assert "resourceNames" not in result

    def test_to_dict_with_resource_names(self):
        """Test converting to dict with resourceNames."""
        rule = PolicyRule(
            api_groups=[""],
            resources=["secrets"],
            verbs=["get"],
            resource_names=["secret1"]
        )
        result = rule.to_dict()
        assert result["resourceNames"] == ["secret1"]


class TestRoleSpec:
    """Tests for RoleSpec model."""

    def test_from_dict(self):
        """Test creating from dict."""
        data = {
            "rules": [
                {"apiGroups": [""], "resources": ["pods"], "verbs": ["get"]}
            ]
        }
        spec = RoleSpec.from_dict(data)
        assert len(spec.rules) == 1
        assert spec.rules[0].resources == ["pods"]

    def test_to_dict(self):
        """Test converting to dict."""
        spec = RoleSpec(rules=[
            PolicyRule(api_groups=[""], resources=["pods"], verbs=["get"])
        ])
        result = spec.to_dict()
        assert len(result["rules"]) == 1


class TestRole:
    """Tests for Role model."""

    def test_from_dict(self, sample_role_body):
        """Test creating Role from dict."""
        role = Role.from_dict(sample_role_body)
        assert role.name == "custom-role"
        assert role.namespace == "default"
        assert len(role.spec.rules) == 1


class TestClusterRole:
    """Tests for ClusterRole model."""

    def test_from_dict(self, sample_cluster_role_body):
        """Test creating ClusterRole from dict."""
        cluster_role = ClusterRole.from_dict(sample_cluster_role_body)
        assert cluster_role.name == "custom-cluster-role"
        assert len(cluster_role.spec.rules) == 1

    def test_to_dict(self, sample_cluster_role):
        """Test converting to dict."""
        result = sample_cluster_role.to_dict()
        assert result["kind"] == "ClusterRole"
        assert "namespace" not in result["metadata"]
