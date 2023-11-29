import logging
from app.config import Config
from app.logging_config import setup_logging
from kubernetes import client
from kubernetes.client.rest import ApiException

from .rbac_handlers import update_crb, update_rb
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


def create_group_handler(body, spec, **kwargs):
    """
    This handler will be called when a Group resource is created.
    It creates the corresponding Kubernetes Role/ClusterRole binding to group.
    """
    # define local variable
    group_name = body['metadata']['name']
    cluster_roles = spec.get('CRoles', [])
    user_namespace = kwargs['namespace']
    roles = spec.get('Roles', [])

    # Create role bindings for each cluster role
    for c_role in cluster_roles:
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="ClusterRole",
                                    name=c_role["clusterRole"])

        if 'namespace' in c_role:
            subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="Group", name=group_name,
                                       namespace=c_role["namespace"])
            binding = client.V1RoleBinding(
                metadata=client.V1ObjectMeta(name=f"{group_name}-{c_role['namespace']}-{c_role['clusterRole']}",
                                             namespace=c_role["namespace"]), role_ref=role_ref, subjects=[subject])
            try:
                rbac_api.create_namespaced_role_binding(namespace=c_role["namespace"], body=binding)
                logger.info(f"Role binding created for user {group_name} and role {c_role}")
            except ApiException as e:
                if e.status == 409:
                    logger.warning(
                        f"\x1b[31mCannot create RoleBinding {binding.metadata.name} because it already exists\x1b[0m")
                else:
                    return logger.exception({'error': str(e)}, exc_info=True)

        else:
            subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="Group", name=group_name)
            binding = client.V1ClusterRoleBinding(
                metadata=client.V1ObjectMeta(name=f"{group_name}-{user_namespace}-{c_role['clusterRole']}"),
                role_ref=role_ref, subjects=[subject])
            try:
                rbac_api.create_cluster_role_binding(body=binding)
                logger.info(f"ClusterRole binding created for group {group_name} and role {c_role}")
            except ApiException as e:
                if e.status == 409:
                    logger.warning(
                        f"\x1b[31mCannot create ClusterRoleBinding {binding.metadata.name} because it already exists\x1b[0m")
                else:
                    return logger.exception({'error': str(e)}, exc_info=True)

    # Create role bindings for role
    for role in roles:
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="Role", name=role)
        subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="User", name=group_name)
        binding = client.V1RoleBinding(
            metadata=client.V1ObjectMeta(name=f"{group_name}-{user_namespace}-{role}", namespace=user_namespace),
            role_ref=role_ref, subjects=[subject])

        try:
            rbac_api.create_namespaced_role_binding(namespace=user_namespace, body=binding)
            logger.info(f"Role binding created for user {group_name} and role {role}")
        except ApiException as e:
            if e.status == 409:
                logger.warning(
                    f"\x1b[31mCannot create RoleBinding {binding.metadata.name} because it already exists\x1b[0m")
            else:
                return logger.exception({'error': str(e)}, exc_info=True)


def update_group_handler(body, spec, **kwargs):
    """
    This handler will be called when a Group is updated.
    It updates the corresponding Kubernetes Role/ClusterRole binding to group.
    """
    # define local variable
    group_name = body['metadata']['name']
    cluster_roles = spec.get('CRoles', [])
    user_namespace = kwargs['namespace']
    roles = spec.get('Roles', [])

    # Iterate over namespaces and remove unused clusterRole bindings to the group
    try:
        update_crb(name=group_name, cr=cluster_roles, kind='Group')
    except ApiException as e:
        return logger.exception({'Exception removing clusterRoleBinding': str(e)}, exc_info=True)

    # Iterate over namespaces and remove unused role bindings to the group
    try:
        update_rb(name=group_name, cr=cluster_roles, kind='Group')
    except ApiException as e:
        return logger.exception({'Exception removing RoleBinding': str(e.reason)}, exc_info=True)

    # Updated role/Cluster role_binding for each cluster role
    for c_role in cluster_roles:
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="ClusterRole",
                                    name=c_role["clusterRole"])

        if 'namespace' in c_role:
            subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="Group", name=group_name,
                                       namespace=c_role["namespace"])
            binding = client.V1RoleBinding(
                metadata=client.V1ObjectMeta(name=f"{group_name}-{c_role['namespace']}-{c_role['clusterRole']}",
                                             namespace=c_role["namespace"]), role_ref=role_ref, subjects=[subject])
            try:
                rbac_api.create_namespaced_role_binding(namespace=c_role["namespace"], body=binding)
                logger.info(f"\x1b[32mAdded RoleBinding {binding.metadata.name} to group {group_name}\x1b[0m")
            except ApiException as e:
                if e.status == 409:
                    rbac_api.patch_namespaced_role_binding(name=binding.metadata.name,
                                                           namespace=binding.metadata.namespace, body=binding)
                else:
                    return logger.exception({'An error occurred': str(e)}, exc_info=True)

        else:
            subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="Group", name=group_name)
            binding = client.V1ClusterRoleBinding(
                metadata=client.V1ObjectMeta(name=f"{group_name}-{user_namespace}-{c_role['clusterRole']}"),
                role_ref=role_ref, subjects=[subject])
            try:
                rbac_api.create_cluster_role_binding(body=binding)
                logger.info(f"\x1b[32mAdded ClusterRoleBinding {binding.metadata.name} to group {group_name}\x1b[0m")
            except ApiException as e:
                if e.status == 409:
                    rbac_api.replace_cluster_role_binding(name=binding.metadata.name, body=binding)
                else:
                    return logger.exception({'An error occurred': str(e)}, exc_info=True)

    # Updated role_binding for role
    for role in roles:
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="Role", name=role)
        subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="Group", name=group_name)
        binding = client.V1RoleBinding(
            metadata=client.V1ObjectMeta(name=f"{group_name}-{user_namespace}-{role}", namespace=user_namespace),
            role_ref=role_ref, subjects=[subject])
        try:
            rbac_api.create_namespaced_role_binding(namespace=user_namespace, body=binding)
            logger.info(f"\x1b[32mAdded RoleBinding {binding.metadata.name} to {group_name}\x1b[0m")
        except ApiException as e:
            if e.status == 409:
                rbac_api.patch_namespaced_role_binding(name=binding.metadata.name, namespace=user_namespace,
                                                       body=binding)
            else:
                return logger.exception({'An error occurred': str(e)}, exc_info=True)


def delete_group_handler(body, **kwargs):
    """
    This handler will be called when a Group resource is deleted.
    It deletes the corresponding Kubernetes Group, Role, and ClusterRole binding attached to it.
    """
    # Define local variables
    custom_api = client.CustomObjectsApi()
    group_name = body['metadata']['name']
    group_ns = body['metadata']['namespace']

    # Iterate over namespaces and remove all role bindings bound to group
    all_namespaces = v1_api.list_namespace().items
    for ns in all_namespaces:
        ns_name = ns.metadata.name
        bindings = rbac_api.list_namespaced_role_binding(namespace=ns_name).items
        for binding in bindings:
            if group_name in [s.name for s in binding.subjects]:
                try:
                    rbac_api.delete_namespaced_role_binding(name=binding.metadata.name, namespace=ns_name)
                    logger.info(f"Role binding '{binding.metadata.name}' deleted in namespace '{ns_name}'")
                except ApiException as e:
                    if e.status == 404:
                        logger.info(f"Role binding '{binding.metadata.name}' not found in namespace '{ns_name}', skipping deletion.")
                    else:
                        raise

    # Iterate over cluster role bindings and remove those bound to group
    try:
        bindings = rbac_api.list_cluster_role_binding()
        for binding in bindings.items:
            if binding and binding.subjects:
                for subject in binding.subjects:
                    if subject.kind == 'Group' and subject.name == group_name:
                        try:
                            rbac_api.read_cluster_role_binding(name=binding.metadata.name)
                            rbac_api.delete_cluster_role_binding(name=binding.metadata.name)
                            logger.info(f"ClusterRoleBinding '{binding.metadata.name}' deleted")
                        except ApiException as e:
                            if e.status == 404:
                                logger.info(f"ClusterRoleBinding '{binding.metadata.name}' not found, skipping deletion.")
                            else:
                                raise
    except ApiException as e:
        logger.error({'An error occurred': str(e.reason)}, exc_info=True)

    # Delete the custom resource
    try:
        custom_api.delete_namespaced_custom_object(
            group=Config.GROUP,
            version="v1",
            namespace=group_ns,
            plural="groups",
            name=group_name,
            body=client.V1DeleteOptions(),
        )
        logger.info(f"Custom resource '{group_name}' deleted successfully.")
    except ApiException as e:
        if e.status != 404:
            logger.exception({f"Exception when deleting custom resource '{group_name}': {e}"}, exc_info=True)
        else:
            logger.info(f"Custom resource '{group_name}' not found, skipping deletion.")
