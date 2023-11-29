import logging
from app.logging_config import setup_logging
from kubernetes import client
from kubernetes.client.rest import ApiException
from .rbac_handlers import update_rb, user_restricted_permissions
from app.config import KubernetesManager
from app.utils.kubeconfig import generate_cluster_config

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

    # Create the resource even if the group does not exist
    sa_body = services_account(user_name)
    to_body = service_account_token(user_name)

    # Create User
    try:
        # Create ServiceAccount
        v1_api.create_namespaced_service_account(namespace=user_namespace, body=sa_body)
        logger.info(f"User {user_name} created.")
    except ApiException as e:
        return {'error': str(e)}

    # Check if the namespace already exists
    if enabled:
        # Create ServiceAccount token and Secret
        try:
            sa_api = client.CoreV1Api()
            sa_api.create_namespaced_secret(namespace=user_namespace, body=to_body)
            logger.info(f"Service account token {user_name} created in namespace {user_namespace}")
        except ApiException as e:
            return {'error': str(e)}

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
                logger.warning(
                    f"\x1b[31mCannot create UserConfigs {user_name}-cluster-context because it already exists\x1b[0m")
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
            ns_name = role.get('namespace')
            cluster_role_name = role.get('clusterRole')
            group_name = role.get('group')

            # Create role bindings for clusterRole
            role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="ClusterRole",
                                        name=cluster_role_name)

            # Create the list of subjects
            subjects = [
                client.V1Subject(api_group=None, kind="ServiceAccount", name=user_name, namespace=user_namespace)]

            # Add group subject only if the group is specified
            if group_name:
                group_subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="Group", name=group_name)
                subjects.append(group_subject)

            binding = client.V1RoleBinding(
                metadata=client.V1ObjectMeta(
                    name=f"{user_name}-{ns_name}-{cluster_role_name}",
                    namespace=ns_name
                ),
                role_ref=role_ref,
                subjects=subjects
            )

            try:
                rbac_api.create_namespaced_role_binding(namespace=role["namespace"], body=binding)
                logger.info(f"Role binding created for user {user_name} and role {role}")
            except ApiException as e:
                return {'error': str(e)}

    # Create role bindings for role
    for role in roles:
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="Role", name=role)

        # Note the apiGroup is set to an empty string for a ServiceAccount
        subject = client.V1Subject(api_group="", kind="ServiceAccount", name=user_name, namespace=user_namespace)

        binding = client.V1RoleBinding(
            metadata=client.V1ObjectMeta(name=f"{user_name}-{user_namespace}-{role}", namespace=user_namespace),
            role_ref=role_ref,
            subjects=[subject]
        )

        try:
            rbac_api.create_namespaced_role_binding(namespace=user_namespace, body=binding)
            logger.info(f"Role binding created for user {user_name} and role {role}")
        except ApiException as e:
            logger.error(
                f"Error creating role binding for {role} in namespace {user_namespace}: {e.reason} - Status: {e.status}")
            return {'error': str(e)}


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
        ns_name = role.get('namespace')
        cluster_role_name = role.get('clusterRole')
        group_name = role.get('group')

        # Create role bindings for clusterRole
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="ClusterRole", name=cluster_role_name)

        # Create the list of subjects
        subjects = [client.V1Subject(api_group=None, kind="ServiceAccount", name=user_name, namespace=user_namespace)]

        # Add group subject only if the group is specified
        if group_name:
            group_subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="Group", name=group_name)
            subjects.append(group_subject)

        binding = client.V1RoleBinding(
            metadata=client.V1ObjectMeta(
                name=f"{user_name}-{ns_name}-{cluster_role_name}",
                namespace=ns_name
            ),
            role_ref=role_ref,
            subjects=subjects
        )

        try:
            rbac_api.create_namespaced_role_binding(namespace=role["namespace"], body=binding)
            logger.info(f"Role binding created for user {user_name} and role {role}")
        except ApiException as e:
            return {'error': str(e)}

    # Update role bindings
    for role in roles:
        role_ref = client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="Role", name=role)
        subject = client.V1Subject(api_group="rbac.authorization.k8s.io", kind="ServiceAccount", name=user_name)
        binding = client.V1RoleBinding(
            metadata=client.V1ObjectMeta(name=f"{user_name}-{user_namespace}-{role}", namespace=user_namespace),
            role_ref=role_ref, subjects=[subject])

        try:
            rbac_api.create_namespaced_role_binding(namespace=user_namespace, body=binding)
            logger.info(f"\x1b[32mAdded RoleBinding {binding.metadata.name} to {user_name}\x1b[0m")
        except client.rest.ApiException as e:
            if e.status == 409:
                rbac_api.patch_namespaced_role_binding(name=binding.metadata.name, namespace=user_namespace,
                                                       body=binding)
            else:
                return logger.exception({'An error occurred': str(e.reason)}, exc_info=True)


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
        v1_api.delete_namespaced_service_account(user_name, user_namespace,
                                                 body=client.V1DeleteOptions(propagation_policy='Foreground',
                                                                             grace_period_seconds=5))
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
        logger.exception({'Exception when reading ClusterRole': str(e.reason)})
        return

    for binding in bindings.items:
        if binding.subjects is None:
            continue

        for subject in binding.subjects:
            if subject.name == user_name and subject.kind == 'ServiceAccount':
                # Check if the ClusterRoleBinding exists before attempting to delete
                try:
                    existing_binding = rbac_api.read_cluster_role_binding(name=binding.metadata.name)
                except ApiException as e:
                    if e.status == 404:
                        logger.warning(f"ClusterRoleBinding {binding.metadata.name} not found, skipping deletion.")
                        continue
                    else:
                        logger.exception({'Exception when reading cluster role_binding': str(e)})
                        continue

                # Proceed with deletion
                try:
                    rbac_api.delete_cluster_role_binding(name=binding.metadata.name)
                    logger.info(f"Removing clusterRole binding {binding.metadata.name}")
                except client.rest.ApiException as e:
                    logger.exception({'Exception when deleting cluster role_binding': str(e.reason)})
