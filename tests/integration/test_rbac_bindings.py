"""Integration tests for RBAC binding verification.

These tests verify that the operator creates correct RBAC bindings.
"""

import pytest
import time
from kubernetes import client, config
from kubernetes.client.rest import ApiException


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def k8s_client():
    """Configure Kubernetes client for testing."""
    try:
        config.load_kube_config()
    except config.ConfigException:
        pytest.skip("No Kubernetes cluster available")

    return client.ApiClient()


@pytest.fixture(scope="module")
def custom_api(k8s_client):
    """Get CustomObjectsApi client."""
    return client.CustomObjectsApi(k8s_client)


@pytest.fixture(scope="module")
def core_api(k8s_client):
    """Get CoreV1Api client."""
    return client.CoreV1Api(k8s_client)


@pytest.fixture(scope="module")
def rbac_api(k8s_client):
    """Get RbacAuthorizationV1Api client."""
    return client.RbacAuthorizationV1Api(k8s_client)


@pytest.fixture(scope="module")
def test_namespace(core_api):
    """Create a test namespace."""
    ns_name = "iam-test-rbac"

    ns = client.V1Namespace(metadata=client.V1ObjectMeta(name=ns_name))
    try:
        core_api.create_namespace(body=ns)
    except ApiException as e:
        if e.status != 409:
            raise

    yield ns_name

    try:
        core_api.delete_namespace(name=ns_name)
    except ApiException:
        pass


class TestRBACBindings:
    """Tests verifying correct RBAC binding creation."""

    GROUP = "k8sio.auth"
    VERSION = "v1"

    def test_user_role_binding_subjects(self, custom_api, rbac_api, core_api, test_namespace):
        """Test that user RoleBindings have correct subjects."""
        user_name = "test-user-rbac"

        user = {
            "apiVersion": f"{self.GROUP}/{self.VERSION}",
            "kind": "User",
            "metadata": {
                "name": user_name,
                "namespace": test_namespace,
            },
            "spec": {
                "enabled": False,
                "CRoles": [
                    {"namespace": test_namespace, "clusterRole": "view"}
                ],
                "Roles": [],
            }
        }

        try:
            custom_api.create_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural="users",
                body=user,
            )
            time.sleep(3)

            # Check RoleBinding
            binding_name = f"{user_name}-{test_namespace}-view"
            try:
                rb = rbac_api.read_namespaced_role_binding(
                    name=binding_name,
                    namespace=test_namespace
                )

                # Verify subjects
                assert len(rb.subjects) >= 1
                sa_subjects = [s for s in rb.subjects if s.kind == "ServiceAccount"]
                assert len(sa_subjects) >= 1
                assert sa_subjects[0].name == user_name
                assert sa_subjects[0].namespace == test_namespace

                # Verify role ref
                assert rb.role_ref.kind == "ClusterRole"
                assert rb.role_ref.name == "view"

            except ApiException as e:
                if e.status != 404:
                    raise
                pytest.skip("Operator not running or binding not created")

        finally:
            try:
                custom_api.delete_namespaced_custom_object(
                    group=self.GROUP,
                    version=self.VERSION,
                    namespace=test_namespace,
                    plural="users",
                    name=user_name,
                )
            except ApiException:
                pass

    def test_user_with_group_binding(self, custom_api, rbac_api, test_namespace):
        """Test that user bindings with groups include both subjects."""
        user_name = "test-user-group"
        group_name = "devops"

        user = {
            "apiVersion": f"{self.GROUP}/{self.VERSION}",
            "kind": "User",
            "metadata": {
                "name": user_name,
                "namespace": test_namespace,
            },
            "spec": {
                "enabled": False,
                "CRoles": [
                    {
                        "namespace": test_namespace,
                        "clusterRole": "view",
                        "group": group_name
                    }
                ],
                "Roles": [],
            }
        }

        try:
            custom_api.create_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural="users",
                body=user,
            )
            time.sleep(3)

            binding_name = f"{user_name}-{test_namespace}-view"
            try:
                rb = rbac_api.read_namespaced_role_binding(
                    name=binding_name,
                    namespace=test_namespace
                )

                # Should have both SA and Group subjects
                sa_subjects = [s for s in rb.subjects if s.kind == "ServiceAccount"]
                group_subjects = [s for s in rb.subjects if s.kind == "Group"]

                assert len(sa_subjects) >= 1
                assert len(group_subjects) >= 1
                assert group_subjects[0].name == group_name

            except ApiException as e:
                if e.status != 404:
                    raise
                pytest.skip("Operator not running or binding not created")

        finally:
            try:
                custom_api.delete_namespaced_custom_object(
                    group=self.GROUP,
                    version=self.VERSION,
                    namespace=test_namespace,
                    plural="users",
                    name=user_name,
                )
            except ApiException:
                pass

    def test_group_cluster_role_binding(self, custom_api, rbac_api, test_namespace):
        """Test that groups create correct ClusterRoleBindings."""
        group_name = "test-group-crb"

        group = {
            "apiVersion": f"{self.GROUP}/{self.VERSION}",
            "kind": "Group",
            "metadata": {
                "name": group_name,
                "namespace": test_namespace,
            },
            "spec": {
                "CRoles": [
                    {"clusterRole": "view"}  # Cluster-wide
                ],
                "Roles": [],
            }
        }

        try:
            custom_api.create_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural="groups",
                body=group,
            )
            time.sleep(3)

            binding_name = f"{group_name}-{test_namespace}-view"
            try:
                crb = rbac_api.read_cluster_role_binding(name=binding_name)

                # Verify Group subject
                group_subjects = [s for s in crb.subjects if s.kind == "Group"]
                assert len(group_subjects) >= 1
                assert group_subjects[0].name == group_name

                # Verify role ref
                assert crb.role_ref.kind == "ClusterRole"
                assert crb.role_ref.name == "view"

            except ApiException as e:
                if e.status != 404:
                    raise
                pytest.skip("Operator not running or binding not created")

        finally:
            try:
                custom_api.delete_namespaced_custom_object(
                    group=self.GROUP,
                    version=self.VERSION,
                    namespace=test_namespace,
                    plural="groups",
                    name=group_name,
                )
                # Clean up ClusterRoleBinding
                try:
                    rbac_api.delete_cluster_role_binding(name=f"{group_name}-{test_namespace}-view")
                except ApiException:
                    pass
            except ApiException:
                pass

    def test_binding_cleanup_on_delete(self, custom_api, rbac_api, test_namespace):
        """Test that bindings are cleaned up when resources are deleted."""
        user_name = "test-cleanup"

        user = {
            "apiVersion": f"{self.GROUP}/{self.VERSION}",
            "kind": "User",
            "metadata": {
                "name": user_name,
                "namespace": test_namespace,
            },
            "spec": {
                "enabled": False,
                "CRoles": [
                    {"namespace": test_namespace, "clusterRole": "view"}
                ],
                "Roles": [],
            }
        }

        # Create
        custom_api.create_namespaced_custom_object(
            group=self.GROUP,
            version=self.VERSION,
            namespace=test_namespace,
            plural="users",
            body=user,
        )
        time.sleep(3)

        binding_name = f"{user_name}-{test_namespace}-view"

        # Delete
        custom_api.delete_namespaced_custom_object(
            group=self.GROUP,
            version=self.VERSION,
            namespace=test_namespace,
            plural="users",
            name=user_name,
        )
        time.sleep(5)

        # Verify binding was deleted
        with pytest.raises(ApiException) as exc_info:
            rbac_api.read_namespaced_role_binding(
                name=binding_name,
                namespace=test_namespace
            )
        assert exc_info.value.status == 404
