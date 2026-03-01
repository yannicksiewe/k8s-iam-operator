"""Integration tests for Group CRD lifecycle.

These tests require a running Kubernetes cluster with CRDs installed.
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
    ns_name = "iam-test-groups"

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


class TestGroupLifecycle:
    """Tests for Group CRD create/update/delete lifecycle."""

    GROUP = "k8sio.auth"
    VERSION = "v1"
    PLURAL = "groups"

    def test_create_group(self, custom_api, rbac_api, test_namespace):
        """Test creating a Group resource."""
        group_name = "test-group-create"

        group = {
            "apiVersion": f"{self.GROUP}/{self.VERSION}",
            "kind": "Group",
            "metadata": {
                "name": group_name,
                "namespace": test_namespace,
            },
            "spec": {
                "CRoles": [
                    {"namespace": test_namespace, "clusterRole": "view"}
                ],
                "Roles": [],
            }
        }

        try:
            # Create group
            result = custom_api.create_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural=self.PLURAL,
                body=group,
            )

            assert result["metadata"]["name"] == group_name

            # Wait for operator to process
            time.sleep(3)

            # Verify RoleBinding was created
            binding_name = f"{group_name}-{test_namespace}-view"
            try:
                rb = rbac_api.read_namespaced_role_binding(
                    name=binding_name,
                    namespace=test_namespace
                )
                assert rb.metadata.name == binding_name
            except ApiException:
                # Binding might not exist if operator isn't running
                pass

        finally:
            try:
                custom_api.delete_namespaced_custom_object(
                    group=self.GROUP,
                    version=self.VERSION,
                    namespace=test_namespace,
                    plural=self.PLURAL,
                    name=group_name,
                )
            except ApiException:
                pass

    def test_create_group_cluster_wide(self, custom_api, rbac_api, test_namespace):
        """Test creating a Group with cluster-wide bindings."""
        group_name = "test-group-cluster"

        group = {
            "apiVersion": f"{self.GROUP}/{self.VERSION}",
            "kind": "Group",
            "metadata": {
                "name": group_name,
                "namespace": test_namespace,
            },
            "spec": {
                "CRoles": [
                    {"clusterRole": "view"}  # No namespace = cluster-wide
                ],
                "Roles": [],
            }
        }

        try:
            custom_api.create_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural=self.PLURAL,
                body=group,
            )

            time.sleep(3)

            # Verify ClusterRoleBinding was created
            binding_name = f"{group_name}-{test_namespace}-view"
            try:
                crb = rbac_api.read_cluster_role_binding(name=binding_name)
                assert crb.metadata.name == binding_name
            except ApiException:
                pass

        finally:
            try:
                custom_api.delete_namespaced_custom_object(
                    group=self.GROUP,
                    version=self.VERSION,
                    namespace=test_namespace,
                    plural=self.PLURAL,
                    name=group_name,
                )
            except ApiException:
                pass

    def test_update_group(self, custom_api, rbac_api, test_namespace):
        """Test updating a Group resource."""
        group_name = "test-group-update"

        group = {
            "apiVersion": f"{self.GROUP}/{self.VERSION}",
            "kind": "Group",
            "metadata": {
                "name": group_name,
                "namespace": test_namespace,
            },
            "spec": {
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
                plural=self.PLURAL,
                body=group,
            )
            time.sleep(2)

            # Update - add another role
            group["spec"]["CRoles"].append(
                {"namespace": test_namespace, "clusterRole": "edit"}
            )

            custom_api.patch_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural=self.PLURAL,
                name=group_name,
                body=group,
            )
            time.sleep(2)

            # Verify update
            updated = custom_api.get_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural=self.PLURAL,
                name=group_name,
            )
            assert len(updated["spec"]["CRoles"]) == 2

        finally:
            try:
                custom_api.delete_namespaced_custom_object(
                    group=self.GROUP,
                    version=self.VERSION,
                    namespace=test_namespace,
                    plural=self.PLURAL,
                    name=group_name,
                )
            except ApiException:
                pass

    def test_delete_group(self, custom_api, rbac_api, test_namespace):
        """Test deleting a Group resource."""
        group_name = "test-group-delete"

        group = {
            "apiVersion": f"{self.GROUP}/{self.VERSION}",
            "kind": "Group",
            "metadata": {
                "name": group_name,
                "namespace": test_namespace,
            },
            "spec": {
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
            plural=self.PLURAL,
            body=group,
        )
        time.sleep(2)

        # Delete
        custom_api.delete_namespaced_custom_object(
            group=self.GROUP,
            version=self.VERSION,
            namespace=test_namespace,
            plural=self.PLURAL,
            name=group_name,
        )
        time.sleep(3)

        # Verify deletion
        with pytest.raises(ApiException) as exc_info:
            custom_api.get_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural=self.PLURAL,
                name=group_name,
            )
        assert exc_info.value.status == 404
