import logging
from app.config import KubernetesManager
from app.logging_config import setup_logging
from kubernetes import client
from kubernetes.client import ApiException


# Configure the logging instance, format and level
#
setup_logging()
logger = logging.getLogger(__name__)
api_client = KubernetesManager.configure_kubernetes_client()
rbac_api = client.RbacAuthorizationV1Api(api_client)


def update_crb(name, cr, kind):
    # Call the function to load the cluster configuration
    name = name
    cluster_roles = cr

    # Iterate over namespaces and remove unused clusterRole bindings to group
    user_cluster_roles = [role["clusterRole"] for role in cluster_roles if "namespace" not in role]
    existing_cluster_roles = rbac_api.list_cluster_role_binding()
    crb_to_delete = []
    for binding in existing_cluster_roles.items:
        if binding and binding.subjects:
            for subject in binding.subjects:
                if subject.kind == kind and subject.name == name:
                    if binding.role_ref.name not in user_cluster_roles:
                        crb = binding.metadata.name
                        crb_to_delete.append(crb)
                        try:
                            rbac_api.delete_cluster_role_binding(name=crb)
                            logger.info(f"\033[38;5;208mClusterRoleBinding {crb} Remove to group {name}\033[0m")
                        except ApiException as e:
                            return logger.exception({'error': str(e)}, exc_info=True)
    return crb_to_delete


# def update_cr(body, spec, kind, **kwargs):
def update_rb(name, cr, kind):
    # Call the function to load the cluster configuration
    core_v1 = client.CoreV1Api(api_client)
    name = name
    cluster_roles = cr

    # Iterate over namespaces and remove unused role bindings to group
    all_namespaces = core_v1.list_namespace().items
    user_cluster_roles = [(role['namespace'], role["clusterRole"]) for role in cluster_roles if "namespace" in role]
    rb_to_delete = []
    for ns in all_namespaces:
        ns_name = ns.metadata.name
        existing_roles = rbac_api.list_namespaced_role_binding(namespace=ns_name).items
        for r_binding in existing_roles:
            if r_binding and r_binding.subjects:
                for r_subject in r_binding.subjects:
                    if kind == 'Group':
                        if len(r_binding.subjects) == 1 and r_subject.kind == 'Group' and r_subject.name == name:
                            if r_binding.role_ref.name not in user_cluster_roles:
                                rb_name = r_binding.metadata.name
                                rb_nspace = r_binding.metadata.namespace
                                rb_to_delete.append((rb_name, rb_nspace))
                                try:
                                    rbac_api.delete_namespaced_role_binding(name=rb_name, namespace=rb_nspace)
                                    logger.info(f"\033[38;5;208mRoleBinding {rb_name} Remove to {name}\033[0m")
                                except ApiException as e:
                                    return logger.exception({'error': str(e)}, exc_info=True)
                    else:
                        if kind == 'ServiceAccount':
                            if r_subject.kind == 'ServiceAccount' and r_subject.name == name:
                                if (r_binding.metadata.namespace, r_binding.role_ref.name) not in user_cluster_roles:
                                    rb_name = r_binding.metadata.name
                                    rb_nspace = r_binding.metadata.namespace
                                    rb_to_delete.append((rb_name, rb_nspace))
                                    try:
                                        rbac_api.delete_namespaced_role_binding(name=rb_name, namespace=rb_nspace)
                                        logger.info(f"\033[38;5;208mRoleBinding {rb_name} Remove to {name}\033[0m")
                                    except ApiException as e:
                                        return logger.exception({'error': str(e)}, exc_info=True)
    return rb_to_delete


def user_restricted_permissions(body, spec):
    # Call the function to load the cluster configuration
    user_name = body['metadata']['name']
    user_namespace = body['metadata']['namespace']

    cluster_roles = spec.get('CRoles', [])
    restricted_namespaces = list(set([role["namespace"] for role in cluster_roles] + ["default", f"{user_name}"]))

    # Create the ClusterRole
    cr = client.V1ClusterRole(
        metadata=client.V1ObjectMeta(name=f"{user_name}-restricted-namespace-role"),
        rules=[client.V1PolicyRule(
            api_groups=[""],
            resources=["*"],
            verbs=["get", "watch", "list"],
            resource_names=restricted_namespaces
        )]
    )

    try:
        rbac_api.create_cluster_role(cr)
        logger.info(f"Restricted namespace ClusterRole '{user_name}-restricted-namespace-role' created")
    except ApiException as e:
        if e.status == 409:
            rbac_api.patch_cluster_role(name=cr.metadata.name, body=cr)
            logger.info(f"Restricted namespace ClusterRole '{user_name}-restricted-namespace-role' updated")
        else:
            logger.exception({'Exception when creating restricted namespace ClusterRole': str(e)}, exc_info=True)
            return

    # Create the ClusterRolebinding
    crb = client.V1ClusterRoleBinding(
        metadata=client.V1ObjectMeta(name=f"{user_name}-restricted-namespace-binding"),
        role_ref=client.V1RoleRef(
            api_group="rbac.authorization.k8s.io",
            kind="ClusterRole",
            name=f"{user_name}-restricted-namespace-role"
        ),
        subjects=[client.V1Subject(
            kind="ServiceAccount",
            name=user_name,
            namespace=user_namespace
        )]
    )

    try:
        rbac_api.create_cluster_role_binding(body=crb)
        logger.info(f"Restricted namespace ClusterRoleBinding '{user_name}-restricted-namespace-binding' created")
    except ApiException as e:
        if e.status == 409:
            rbac_api.patch_cluster_role_binding(name=crb.metadata.name, body=crb)
            logger.info(f"Restricted namespace ClusterRoleBinding '{user_name}-restricted-namespace-binding' updated")
        else:
            logger.exception({'Exception when creating restricted namespace ClusterRoleBinding': str(e)}, exc_info=True)
            return
