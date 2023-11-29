import time
import logging
from app.logging_config import setup_logging
from kubernetes import client
from kubernetes.client.rest import ApiException
from app.config import KubernetesManager


# Configure the logging instance, format and level
#
setup_logging()
logger = logging.getLogger(__name__)

# Initialize Kubernetes API client
k8s_client = KubernetesManager.configure_kubernetes_client()
v1_api = client.CoreV1Api(k8s_client)
rbac_api = client.RbacAuthorizationV1Api(k8s_client)
services_account = KubernetesManager.create_service_account
service_account_token = KubernetesManager.create_service_account_token


def create_role_handler(spec, **kwargs):
    """
    This handler will be called when a Role/ClusterRole resource is created.
    It creates/updates the corresponding Kubernetes Role/ClusterRole object.
    """
    max_retries = 2
    retry_count = 0

    # Check and retry for namespace existence if it's a Role
    if kwargs['body']['kind'] == 'Role':
        while retry_count <= max_retries:
            try:
                v1_api.read_namespace(name=kwargs['namespace'])
                break  # Namespace exists, exit retry loop
            except ApiException as e:
                if e.status == 404:
                    logger.warning(f"Namespace '{kwargs['namespace']}' not found, retrying...")
                    retry_count += 1
                    time.sleep(5)  # Wait for 5 seconds before retrying
                else:
                    logger.exception(f"Exception when checking namespace existence: {e.reason}")
                    return  # Exit function on non-retryable error

        if retry_count > max_retries:
            logger.error(f"Maximum retries reached. Namespace '{kwargs['namespace']}' may not exist.")
            return  # Exit function as namespace check failed after retries

    # Process Role or ClusterRole creation/update
    if kwargs['body']['kind'] == 'Role':
        body = client.V1Role(
            metadata=client.V1ObjectMeta(name=kwargs['body']['metadata']['name']),
            rules=spec.get('rules', [])
        )
        try:
            # Check if the Role already exists
            rbac_api.read_namespaced_role(namespace=kwargs['namespace'], name=kwargs['body']['metadata']['name'])
            rbac_api.patch_namespaced_role(name=kwargs['body']['metadata']['name'], namespace=kwargs['namespace'],
                                           body=body)
            logger.info(f"Role '{body.metadata.name}' updated")
        except ApiException as e:
            if e.status == 404:
                rbac_api.create_namespaced_role(namespace=kwargs['namespace'], body=body)
                logger.info(f"Role '{body.metadata.name}' created")
            else:
                logger.exception(f"Exception when creating/updating Role: {e.reason}")

    elif kwargs['body']['kind'] == 'ClusterRole':
        body = client.V1ClusterRole(
            metadata=client.V1ObjectMeta(name=kwargs['body']['metadata']['name']),
            rules=spec.get('rules', [])
        )
        try:
            # Check if the ClusterRole already exists
            rbac_api.read_cluster_role(name=kwargs['body']['metadata']['name'])
            rbac_api.patch_cluster_role(name=kwargs['body']['metadata']['name'], body=body)
            logger.info(f"ClusterRole '{body.metadata.name}' updated")
        except ApiException as e:
            if e.status == 404:
                rbac_api.create_cluster_role(body=body)
                logger.info(f"ClusterRole '{body.metadata.name}' created")
            else:
                logger.exception(f"Exception when creating ClusterRole: {e.reason}")
    else:
        logger.warning(f"Unsupported kind '{kwargs['body']['kind']}'")


def delete_role_handler(**kwargs):
    """
    This handler will be called when a Role/ClusterRole resource is deleted.
    It deletes the corresponding Kubernetes Role/ClusterRole object.
    """
    try:
        if kwargs['body']['kind'] == 'Role':
            logger.info(
                f"Attempting to delete Role '{kwargs['body']['metadata']['name']}' in namespace '{kwargs['namespace']}'")
            rbac_api.delete_namespaced_role(name=kwargs['body']['metadata']['name'], namespace=kwargs['namespace'])
            logger.info(f"Successfully deleted Role '{kwargs['body']['metadata']['name']}'")

        elif kwargs['body']['kind'] == 'ClusterRole':
            logger.info(f"Attempting to delete ClusterRole '{kwargs['body']['metadata']['name']}'")
            rbac_api.delete_cluster_role(name=kwargs['body']['metadata']['name'])
            logger.info(f"Successfully deleted ClusterRole '{kwargs['body']['metadata']['name']}'")

        else:
            logger.warning(f"Unsupported kind '{kwargs['body']['kind']}'")

    except ApiException as e:
        if e.status == 404:
            logger.info(
                f"Role or ClusterRole '{kwargs['body']['metadata']['name']}' not found. It may have already been deleted.")
        else:
            logger.exception(f"Exception when deleting Role or ClusterRole: {e.reason}")