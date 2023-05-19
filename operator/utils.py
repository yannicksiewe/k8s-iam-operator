from kubernetes import client, config
from kubernetes.client import ApiException


# def configure_kubernetes_client():
#     config.load_kube_config()
#     api_client = client.ApiClient()
#     core_v1 = client.CoreV1Api(api_client=api_client)
#     rbac_v1 = client.RbacAuthorizationV1Api(api_client=api_client)
#     return core_v1, rbac_v1


def configure_kubernetes_client():
    # Load the in-cluster configuration
    config.load_incluster_config()

    # Retrieve the ServiceAccount token and namespace
    token_path = '/var/run/secrets/kubernetes.io/serviceaccount/token'
    namespace_path = '/var/run/secrets/kubernetes.io/serviceaccount/namespace'

    with open(token_path, 'r') as f:
        token = f.read().strip()

    with open(namespace_path, 'r') as f:
        namespace = f.read().strip()

    # Create a Kubernetes client configuration object and set the BearerToken field
    configuration = client.Configuration()
    configuration.host = 'https://kubernetes.default.svc'
    configuration.verify_ssl = False
    configuration.debug = False
    configuration.debugging = False
    configuration.ssl_ca_cert = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
    configuration.cert_file = '/var/run/secrets/kubernetes.io/serviceaccount/client.crt'
    configuration.key_file = '/var/run/secrets/kubernetes.io/serviceaccount/client.key'
    configuration.api_key['authorization'] = 'Bearer ' + token
    configuration.namespace = namespace

    # Use the client configuration object to create a Kubernetes API client
    api_client = client.api_client.ApiClient(configuration)

    return api_client


def services_account(name):
    sa_body = client.V1ServiceAccount(
        metadata=client.V1ObjectMeta(name=name),
        automount_service_account_token=True,
    )
    return sa_body


def update_crb(name, cr, kind):
    rbac_api = client.RbacAuthorizationV1Api()
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
                            print(f"\033[38;5;208mClusterRoleBinding {crb} Remove to group {name}\033[0m")
                        except ApiException as e:
                            return {'error': str(e)}
    return crb_to_delete


# def update_cr(body, spec, kind, **kwargs):
def update_rb(name, cr, kind):
    core_v1 = client.CoreV1Api()
    rbac_api = client.RbacAuthorizationV1Api()
    name = name
    cluster_roles = cr

    # Iterate over namespaces and remove unused role bindings to group
    all_namespaces = core_v1.list_namespace().items
    # user_cluster_roles = [role["clusterRole"] for role in cluster_roles if "namespace" in role]
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
                    else:
                        if kind == 'ServiceAccount':
                            if r_subject.kind == 'ServiceAccount' and r_subject.name == name:
                                if (r_binding.metadata.namespace, r_binding.role_ref.name) not in user_cluster_roles:
                                    rb_name = r_binding.metadata.name
                                    rb_nspace = r_binding.metadata.namespace
                                    rb_to_delete.append((rb_name, rb_nspace))
                                    try:
                                        rbac_api.delete_namespaced_role_binding(name=rb_name, namespace=rb_nspace)
                                        print(f"\033[38;5;208mRoleBinding {rb_name} Remove to {name}\033[0m")
                                    except ApiException as e:
                                        return {'error': str(e)}
    return rb_to_delete


def user_restricted_permissions(body, spec):
    rbac_api = client.RbacAuthorizationV1Api()
    user_name = body['metadata']['name']
    user_namespace = body['metadata']['namespace']
    cluster_roles = spec.get('CRoles', [])
    restricted_namespaces = list(set([role["namespace"] for role in cluster_roles] + ["default", f"{user_name}"]))

    # Create the ClusterRole
    crb = client.V1ClusterRoleBinding(
        metadata=client.V1ObjectMeta(name=f"{user_name}-restricted-namespace-binding"),
        role_ref=client.V1RoleRef(api_group="rbac.authorization.k8s.io", kind="ClusterRole",
                                  name=f"{user_name}-restricted-namespace-role"),
        subjects=[client.V1Subject(kind="ServiceAccount", name=user_name, namespace=user_namespace)]
    )
    try:
        rbac_api.create_cluster_role_binding(body=crb)
        print("Restricted namespace ClusterRole binding created.")
    except ApiException as e:
        if e.status == 409:
            rbac_api.patch_cluster_role_binding(name=crb.metadata.name, body=crb)
            # print("Restricted namespace ClusterRole binding already exists.")
        else:
            print("Error creating restricted namespace ClusterRole binding:", e)

    # Create the ClusterRole
    cr = client.V1ClusterRole(metadata=client.V1ObjectMeta(name=f"{user_name}-restricted-namespace-role"),
                              rules=[client.V1PolicyRule(api_groups=[""], resources=["namespaces"],
                                                         verbs=["get", "watch", "list"],
                                                         resource_names=restricted_namespaces)])
    try:
        rbac_api.create_cluster_role(cr)
        print("Restricted namespace ClusterRole created.")
    except ApiException as e:
        if e.status == 409:
            rbac_api.patch_cluster_role(name=cr.metadata.name, body=cr)
            # print("Restricted namespace ClusterRole already exists.")
        else:
            print("Error creating restricted namespace ClusterRole:", e)
