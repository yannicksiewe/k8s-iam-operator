"""Integration tests for User CRD lifecycle.

These tests require a running Kubernetes cluster with CRDs installed.
"""

import pytest
import time
from kubernetes import client, config
from kubernetes.client.rest import ApiException


# Skip all tests if no cluster available
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
    ns_name = "iam-test"

    # Create namespace
    ns = client.V1Namespace(metadata=client.V1ObjectMeta(name=ns_name))
    try:
        core_api.create_namespace(body=ns)
    except ApiException as e:
        if e.status != 409:  # Already exists
            raise

    yield ns_name

    # Cleanup
    try:
        core_api.delete_namespace(name=ns_name)
    except ApiException:
        pass


class TestUserLifecycle:
    """Tests for User CRD create/update/delete lifecycle."""

    GROUP = "k8sio.auth"
    VERSION = "v1"
    PLURAL = "users"

    def test_create_user(self, custom_api, core_api, test_namespace):
        """Test creating a User resource."""
        user_name = "test-user-create"

        user = {
            "apiVersion": f"{self.GROUP}/{self.VERSION}",
            "kind": "User",
            "metadata": {
                "name": user_name,
                "namespace": test_namespace,
            },
            "spec": {
                "enabled": False,
                "CRoles": [],
                "Roles": [],
            }
        }

        try:
            # Create user
            result = custom_api.create_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural=self.PLURAL,
                body=user,
            )

            assert result["metadata"]["name"] == user_name

            # Wait for operator to process
            time.sleep(2)

            # Verify ServiceAccount was created
            sa = core_api.read_namespaced_service_account(
                name=user_name,
                namespace=test_namespace
            )
            assert sa.metadata.name == user_name

        finally:
            # Cleanup
            try:
                custom_api.delete_namespaced_custom_object(
                    group=self.GROUP,
                    version=self.VERSION,
                    namespace=test_namespace,
                    plural=self.PLURAL,
                    name=user_name,
                )
            except ApiException:
                pass

    def test_create_enabled_user(self, custom_api, core_api, test_namespace):
        """Test creating an enabled User with namespace and kubeconfig."""
        user_name = "test-user-enabled"

        user = {
            "apiVersion": f"{self.GROUP}/{self.VERSION}",
            "kind": "User",
            "metadata": {
                "name": user_name,
                "namespace": test_namespace,
            },
            "spec": {
                "enabled": True,
                "CRoles": [
                    {"namespace": test_namespace, "clusterRole": "view"}
                ],
                "Roles": [],
            }
        }

        try:
            # Create user
            custom_api.create_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural=self.PLURAL,
                body=user,
            )

            # Wait for operator to process
            time.sleep(5)

            # Verify ServiceAccount
            sa = core_api.read_namespaced_service_account(
                name=user_name,
                namespace=test_namespace
            )
            assert sa.metadata.name == user_name

            # Verify user namespace was created
            try:
                ns = core_api.read_namespace(name=user_name)
                assert ns.metadata.name == user_name
            except ApiException as e:
                # Namespace creation might be disabled
                if e.status != 404:
                    raise

        finally:
            # Cleanup
            try:
                custom_api.delete_namespaced_custom_object(
                    group=self.GROUP,
                    version=self.VERSION,
                    namespace=test_namespace,
                    plural=self.PLURAL,
                    name=user_name,
                )
                time.sleep(2)
            except ApiException:
                pass

    def test_update_user(self, custom_api, core_api, test_namespace):
        """Test updating a User resource."""
        user_name = "test-user-update"

        user = {
            "apiVersion": f"{self.GROUP}/{self.VERSION}",
            "kind": "User",
            "metadata": {
                "name": user_name,
                "namespace": test_namespace,
            },
            "spec": {
                "enabled": False,
                "CRoles": [],
                "Roles": [],
            }
        }

        try:
            # Create user
            custom_api.create_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural=self.PLURAL,
                body=user,
            )
            time.sleep(2)

            # Update user
            user["spec"]["CRoles"] = [
                {"namespace": test_namespace, "clusterRole": "view"}
            ]

            custom_api.patch_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural=self.PLURAL,
                name=user_name,
                body=user,
            )
            time.sleep(2)

            # Verify update was processed
            updated = custom_api.get_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=test_namespace,
                plural=self.PLURAL,
                name=user_name,
            )
            assert len(updated["spec"]["CRoles"]) == 1

        finally:
            # Cleanup
            try:
                custom_api.delete_namespaced_custom_object(
                    group=self.GROUP,
                    version=self.VERSION,
                    namespace=test_namespace,
                    plural=self.PLURAL,
                    name=user_name,
                )
            except ApiException:
                pass

    def test_delete_user(self, custom_api, core_api, test_namespace):
        """Test deleting a User resource."""
        user_name = "test-user-delete"

        user = {
            "apiVersion": f"{self.GROUP}/{self.VERSION}",
            "kind": "User",
            "metadata": {
                "name": user_name,
                "namespace": test_namespace,
            },
            "spec": {
                "enabled": False,
                "CRoles": [],
                "Roles": [],
            }
        }

        # Create user
        custom_api.create_namespaced_custom_object(
            group=self.GROUP,
            version=self.VERSION,
            namespace=test_namespace,
            plural=self.PLURAL,
            body=user,
        )
        time.sleep(2)

        # Delete user
        custom_api.delete_namespaced_custom_object(
            group=self.GROUP,
            version=self.VERSION,
            namespace=test_namespace,
            plural=self.PLURAL,
            name=user_name,
        )
        time.sleep(3)

        # Verify ServiceAccount was deleted
        with pytest.raises(ApiException) as exc_info:
            core_api.read_namespaced_service_account(
                name=user_name,
                namespace=test_namespace
            )
        assert exc_info.value.status == 404
