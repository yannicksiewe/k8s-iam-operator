import logging
from kubernetes import client
from kubernetes.client.rest import ApiException
from utils import configure_kubernetes_client
from utils import services_account, update_crb, update_rb, user_restricted_permissions
from kubeconfig import generate_cluster_config

# Configure the logging instance, format and level
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Kubernetes API client
k8s_client = configure_kubernetes_client()
v1_api = client.CoreV1Api(k8s_client)
rbac_api = client.RbacAuthorizationV1Api(k8s_client)


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
                rbac_api.patch_namespaced_role_binding(name=binding.metadata.name, namespace=user_namespace, body=binding)
            else:
                return logger.exception({'An error occurred': str(e)}, exc_info=True)


def update_user_handler(body, spec, **kwargs):
    """
    This handler will be called when a User is updated.
    It updates the corresponding Kubernetes Resources.
    """
    # define local variable
    user_name = body['metadata']['name']
    cluster_roles = spec.get('CRoles', [])
    enabled = spec.get('enabled', False)
    user_namespace = kwargs['namespace']
    roles = spec.get('Roles', [])
    sa_body = services_account(user_name)

    # Update User
    try:
        v1_api.patch_namespaced_service_account(name=user_name, namespace=user_namespace, body=sa_body)
    except ApiException as e:
        return logger.exception({'An error occurred': str(e)}, exc_info=True)

    # Check if the namespace already exists
    if enabled:
        try:
            user_restricted_permissions(body=body, spec=spec)
        except ApiException as e:
            return logger.exception({'Exception updating user restricted permission': str(e)}, exc_info=True)

        try:
            v1_api.read_namespace(user_name)
        except ApiException as e:
            if e.status == 404:
                # Namespace does not exist, so create it
                ns = client.V1Namespace(metadata=client.V1ObjectMeta(name=user_name))
                v1_api.create_namespace(ns)
                logger.info(f"Namespace {user_name} created")
                try:
                    generate_cluster_config(body=body)
                    logger.info(f"UserConfigs file {user_name}-cluster-context generated")
                except ApiException as e:
                    return logger.exception({'An error occurred': str(e)}, exc_info=True)
            else:
                return logger.error({'An error occurred': str(e)}, exc_info=True)
    else:
        try:
            body = client.V1DeleteOptions(propagation_policy='Foreground', grace_period_seconds=0)
            v1_api.delete_namespace(user_name, body=body)
            logger.info(f"Namespace {user_name} deleted")
        except ApiException as e:
            return logger.exception({'An error occurred': str(e)}, exc_info=True)

    # Iterate over namespaces and remove unused role bindings to the user
    try:
        update_rb(name=user_name, cr=cluster_roles, kind='ServiceAccount')
    except ApiException as e:
        return logger.exception({'Exception removing clusterRoleBinding': str(e.reason)}, exc_info=True)

    # Update clusterRole bindings
    for role in cluster_roles:
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="ClusterRole", name=role["clusterRole"])
        group_subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="Group", name=role["group"])
        user_subject = client.V1Subject(api_group=None, kind="ServiceAccount", name=user_name, namespace=user_namespace)
        binding = client.V1RoleBinding(metadata=client.V1ObjectMeta(name=f"{user_name}-{role['namespace']}-{role['clusterRole']}",
                                                                    namespace=role["namespace"]), role_ref=role_ref, subjects=[group_subject, user_subject],)
        try:
            rbac_api.create_namespaced_role_binding(namespace=role["namespace"], body=binding)
            logger.info(f"\x1b[32mAdded ClusterRoleBinding {binding.metadata.name} to {user_name}\x1b[0m")
        except client.rest.ApiException as e:
            if e.status == 409:
                rbac_api.patch_namespaced_role_binding(name=binding.metadata.name, namespace=binding.metadata.namespace, body=binding)
            else:
                return logger.exception({'An error occurred': str(e.reason)}, exc_info=True)

    # Update role bindings
    for role in roles:
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="Role", name=role)
        subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="ServiceAccount", name=user_name)
        binding = client.V1RoleBinding(metadata=client.V1ObjectMeta(name=f"{user_name}-{user_namespace}-{role}", namespace=user_namespace), role_ref=role_ref, subjects=[subject])

        try:
            rbac_api.create_namespaced_role_binding(namespace=user_namespace, body=binding)
            logger.info(f"\x1b[32mAdded RoleBinding {binding.metadata.name} to {user_name}\x1b[0m")
        except client.rest.ApiException as e:
            if e.status == 409:
                rbac_api.patch_namespaced_role_binding(name=binding.metadata.name, namespace=user_namespace, body=binding)
            else:
                return logger.exception({'An error occurred': str(e.reason)}, exc_info=True)


def delete_group_handler(body, **kwargs):
    """
    This handler will be called when a Group resource is deleted.
    It deletes the corresponding Kubernetes Group, Role and ClusterRole binding attached to it.
    """
    # define local variable
    custom_api = client.CustomObjectsApi()
    group_name = body['metadata']['name']
    group_ns = body['metadata']['namespace']

    # Iterate over namespaces and remove all clusterRole bindings bind to group
    all_namespaces = v1_api.list_namespace().items
    for ns in all_namespaces:
        ns_name = ns.metadata.name
        bindings = rbac_api.list_namespaced_role_binding(namespace=ns_name).items
        for binding in bindings:
            if group_name in [s.name for s in binding.subjects]:
                try:
                    rbac_api.delete_namespaced_role_binding(name=binding.metadata.name, namespace=ns_name)
                    logger.info(f"Role binding '{binding.metadata.name}' deleted in namespace '{ns_name}'")
                except client.rest.ApiException as e:
                    return logger.exception({'Exception when deleting role_binding': str(e.reason)}, exc_info=True)

    # Iterate over namespaces and remove all role bindings bind to group
    try:
        bindings = rbac_api.list_cluster_role_binding()
        for binding in bindings.items:
            if binding and binding.subjects:
                for subject in binding.subjects:
                    if subject.kind == 'Group' and subject.name == group_name:
                        try:
                            rbac_api.delete_cluster_role_binding(name=binding.metadata.name)
                            logger.info(f"ClusterRoleBinding '{binding.metadata.name}' deleted")
                        except client.rest.ApiException as e:
                            return logger.exception({'Exception when deleting cluster_role_Binding': str(e)}, exc_info=True)
    except client.rest.ApiException as e:
        return logger.error({'An error occurred': str(e.reason)}, exc_info=True)

    # Delete the custom resource TODO: Improve this deletion
    try:
        custom_api.delete_namespaced_custom_object(
            group="k8sio.auth",
            version="v1",
            namespace=group_ns,
            plural="groups",
            name=group_name,
            body=client.V1DeleteOptions(),
        )
        logger.info(f"Custom resource '{group_name}' deleted successfully.")
    except ApiException as e:
        return logger.exception({f"Exception when deleting custom resource '{group_name}': {e}"}, exc_info=True)


def delete_role_handler(**kwargs):
    """
    This handler will be called when a Role/ClusterRole resource is deleted.
    It deletes the corresponding Kubernetes Role/ClusterRole object.
    """
    if kwargs['body']['kind'] == 'Role':
        try:
            rbac_api.delete_namespaced_role(name=kwargs['body']['metadata']['name'], namespace=kwargs['namespace'])
            logger.info(f"Deleting Role '{kwargs['body']['metadata']['name']}'")
        except ApiException as e:
            logger.exception(f"Exception when deleting Role: {e.reason}")
    elif kwargs['body']['kind'] == 'ClusterRole':
        try:
            rbac_api.delete_cluster_role(name=kwargs['body']['metadata']['name'])
            logger.info(f"Deleting ClusterRole '{kwargs['body']['metadata']['name']}'")
        except ApiException as e:
            logger.exception(f"Exception when deleting ClusterRole: {e.reason}")
    else:
        raise logger.warning(f"Unsupported kind '{kwargs['body']['kind']}'")


def delete_user_handler(body, spec, **kwargs):
    """
    This handler will be called when a user is deleted.
    It deletes the corresponding Kubernetes object.
    """
    # define local variable
    user_name = body['metadata']['name']
    user_namespace = kwargs['namespace']
    enabled = spec.get('enabled', False)

    # Delete the service account for the user
    try:
        v1_api.delete_namespaced_service_account(user_name, user_namespace, body=client.V1DeleteOptions(propagation_policy='Foreground', grace_period_seconds=5))
        logger.info(f"Deleting user {user_name}")
    except ApiException as e:
        return {'An error occurred': str(e)}

    # Delete user namespace
    if enabled:
        try:
            body = client.V1DeleteOptions(propagation_policy='Foreground', grace_period_seconds=0)
            v1_api.delete_namespace(user_name, body=body)
            logger.info(f"Namespace {user_name} deleted")
        except ApiException as e:
            return logger.exception({'Exception deleting Namespace': str(e)}, exc_info=True)

    # Iterate over namespaces and delete role bindings for user in each namespace
    all_namespaces = v1_api.list_namespace().items
    for ns in all_namespaces:
        ns_name = ns.metadata.name
        bindings = rbac_api.list_namespaced_role_binding(namespace=ns_name).items
        for binding in bindings:
            if user_name in [s.name for s in binding.subjects]:
                try:
                    rbac_api.delete_namespaced_role_binding(name=binding.metadata.name, namespace=ns_name)
                    logger.info(f"Removing Role binding '{binding.metadata.name}'")
                except client.rest.ApiException as e:
                    return logger.exception({'Exception deleting role_binding': str(e.reason)})

    # Delete ClusterRole bindings bind to user
    try:
        bindings = rbac_api.list_cluster_role_binding()
    except client.rest.ApiException as e:
        return logger.exception({'Exception when reading ClusterRole': str(e.reason)})
    """ 
    checks whether bindings is None. If it is None, the function simply returns without iterating over bindings. 
    Otherwise, the function iterates over bindings as usual 
    """
    if bindings is None:
        logger.warning(f"No cluster role bindings found for user {user_name}")
        return

    for binding in bindings.items:
        if binding.subjects is None:
            continue

        for subject in binding.subjects:
            if subject.name == user_name and subject.kind == 'ServiceAccount':
                try:
                    rbac_api.delete_cluster_role_binding(name=binding.metadata.name)
                    logger.info(f" Removing clusterRole binding {binding.metadata.name}")
                except client.rest.ApiException as e:
                    return logger.exception({'Exception when deleting cluster role_binding': str(e.reason)})
