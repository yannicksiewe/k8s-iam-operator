import logging
from kubernetes import client
from kubernetes.client.rest import ApiException
from utils import configure_kubernetes_client, services_account, user_restricted_permissions
from kubeconfig import generate_cluster_config

# Configure the logging instance, format and level
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Kubernetes API client
k8s_client = configure_kubernetes_client()
v1_api = client.CoreV1Api(k8s_client)
rbac_api = client.RbacAuthorizationV1Api(k8s_client)


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
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="ClusterRole", name=c_role["clusterRole"])

        if 'namespace' in c_role:
            subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="Group", name=group_name, namespace=c_role["namespace"])
            binding = client.V1RoleBinding(metadata=client.V1ObjectMeta(name=f"{group_name}-{c_role['namespace']}-{c_role['clusterRole']}", namespace=c_role["namespace"]), role_ref=role_ref, subjects=[subject])
            try:
                rbac_api.create_namespaced_role_binding(namespace=c_role["namespace"], body=binding)
                logger.info(f"Role binding created for user {group_name} and role {c_role}")
            except ApiException as e:
                if e.status == 409:
                    logger.warning(f"\x1b[31mCannot create RoleBinding {binding.metadata.name} because it already exists\x1b[0m")
                else:
                    return logger.exception({'error': str(e)}, exc_info=True)

        else:
            subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="Group", name=group_name)
            binding = client.V1ClusterRoleBinding(metadata=client.V1ObjectMeta(name=f"{group_name}-{user_namespace}-{c_role['clusterRole']}"), role_ref=role_ref, subjects=[subject])
            try:
                rbac_api.create_cluster_role_binding(body=binding)
                logger.info(f"ClusterRole binding created for group {group_name} and role {c_role}")
            except ApiException as e:
                if e.status == 409:
                    logger.warning(f"\x1b[31mCannot create ClusterRoleBinding {binding.metadata.name} because it already exists\x1b[0m")
                else:
                    return logger.exception({'error': str(e)}, exc_info=True)

    # Create role bindings for role
    for role in roles:
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="Role", name=role)
        subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="User", name=group_name)
        binding = client.V1RoleBinding(metadata=client.V1ObjectMeta(name=f"{group_name}-{user_namespace}-{role}", namespace=user_namespace), role_ref=role_ref, subjects=[subject])

        try:
            rbac_api.create_namespaced_role_binding(namespace=user_namespace, body=binding)
            logger.info(f"Role binding created for user {group_name} and role {role}")
        except ApiException as e:
            if e.status == 409:
                logger.warning(f"\x1b[31mCannot create RoleBinding {binding.metadata.name} because it already exists\x1b[0m")
            else:
                return logger.exception({'error': str(e)}, exc_info=True)


def create_role_handler(spec, **kwargs):
    """
    This handler will be called when a Role/ClusterRole resource is created.
    It creates/updates the corresponding Kubernetes Role/ClusterRole object.
    """
    if kwargs['body']['kind'] == 'Role':
        body = client.V1Role(
            metadata=client.V1ObjectMeta(name=kwargs['body']['metadata']['name']),
            rules=spec.get('rules', [])
        )
        try:
            # Check if the Role already exists
            rbac_api.read_namespaced_role(namespace=kwargs['namespace'], name=kwargs['body']['metadata']['name'])
            rbac_api.patch_namespaced_role(name=kwargs['body']['metadata']['name'], namespace=kwargs['namespace'], body=body)
            logger.info(f"Role '{body.metadata.name}' updated")
        except ApiException as e:
            if e.status == 404:
                rbac_api.create_namespaced_role(namespace=kwargs['namespace'], body=body)
                logger.info(f"Role '{body.metadata.name}' created")
            else:
                logger.exception(f"\x1b[31mException when creating/updating Role\x1b[0m: {e.reason}")

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
                logger.exception(f"\x1b[31mException when creating ClusterRole\x1b[0m: {e.reason}")
    else:
        raise logger.warning(f"Unsupported kind '{kwargs['body']['kind']}'")


def create_user_handler(body, spec, **kwargs):
    """
    This handler will be called when a Group is created.
    It creates the corresponding Kubernetes ServicesAccount, Users and bindings.
    """
    user_name = body['metadata']['name']
    cluster_roles = spec.get('CRoles', [])
    user_namespace = kwargs['namespace']
    roles = spec.get('Roles', [])
    enabled = spec.get('enabled', False)
    sa_body = services_account(user_name)

    # Create User
    try:
        v1_api.create_namespaced_service_account(namespace=user_namespace, body=sa_body)
        logger.info(f"User {user_name} created.")
    except ApiException as e:
        return {'error': str(e)}

    # Check if the namespace already exists
    if enabled:
        try:
            user_restricted_permissions(body=body, spec=spec)
            logger.info("Permissions initialise")
        except ApiException as e:
            return {'error': str(e)}

        try:
            v1_api.read_namespace(user_name)
            logger.info(f"Namespace {user_name} already exists.")
        except ApiException as e:
            if e.status == 404:
                # Namespace does not exist, so create it
                ns = client.V1Namespace(metadata=client.V1ObjectMeta(name=user_name))
                v1_api.create_namespace(ns)
                logger.info(f"Namespace {user_name} created.")
            else:
                # print("Error: %s" % e)
                logger.warning("Error: %s" % e)
        try:
            generate_cluster_config(body=body)
            logger.info(f"UserConfigs file {user_name}-cluster-context generated")
        except ApiException as e:
            if e.status == 409:
                logger.warning(f"\x1b[31mCannot create UserConfigs {user_name}-cluster-context because it already exists\x1b[0m")
            else:
                return {'error': str(e)}
    else:
        pass

    # Create or update role/clusterRole bindings to user
    for namespace in cluster_roles:
        ns_name = namespace['namespace']
        cluster_role_name = namespace['clusterRole']

        # Check if the namespace exists
        try:
            v1_api.read_namespace(name=ns_name)
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"\x1b[31mNamespace '{ns_name}' does not exist\x1b[0m")
            else:
                return {'error': str(e)}

        # Check if the cluster role exists
        try:
            rbac_api.read_cluster_role(name=cluster_role_name)
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"\x1b[31mCluster role '{cluster_role_name}' does not exist\x1b[0m")
            else:
                return {'error': str(e)}

        # Create role bindings for clusterRole
        for role in cluster_roles:
            role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="ClusterRole", name=role["clusterRole"])
            group_subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="Group", name=role["group"])
            user_subject = client.V1Subject(api_group=None, kind="ServiceAccount", name=user_name, namespace=user_namespace)
            binding = client.V1RoleBinding(metadata=client.V1ObjectMeta(name=f"{user_name}-{role['namespace']}-{role['clusterRole']}",
                                                                        namespace=role["namespace"]), role_ref=role_ref, subjects=[group_subject, user_subject],)
            try:
                rbac_api.create_namespaced_role_binding(namespace=role["namespace"], body=binding)
                logger.info(f"Role binding created for user {user_name} and role {role}")
            except ApiException as e:
                return {'error': str(e)}

    # Create role bindings for role
    for role in roles:
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="Role", name=role)
        subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="ServiceAccount", name=user_name)
        binding = client.V1RoleBinding(metadata=client.V1ObjectMeta(name=f"{user_name}-{user_namespace}-{role}", namespace=user_namespace), role_ref=role_ref, subjects=[subject])

        try:
            rbac_api.create_namespaced_role_binding(namespace=user_namespace, body=binding)
            logger.info(f"Role binding created for user {user_name} and role {role}")
        except ApiException as e:
            return {'error': str(e)}
