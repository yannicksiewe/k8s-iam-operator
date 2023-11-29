import os
from kubernetes import client, config


class Config:
    GROUP = os.environ.get('GROUP_NAME', 'k8sio.auth')
    VERSION = os.environ.get('VERSION', 'v1')
    PLURAL = os.environ.get('PLURAL', 'users')
    GPLURAL = os.environ.get('GROUP_PLURAL', 'groups')
    RPLURAL = os.environ.get('ROLE_PLURAL', 'roles')
    CRPLURAL = os.environ.get('CLUSTER_ROLE_PLURAL', 'clusterroles')
    TEMPO_ENDPOINT = os.environ.get('TEMPO_ENDPOINT', 'clusterroles')


class KubernetesManager:
    def __init__(self):
        self.api_client = self.configure_kubernetes_client()

    @staticmethod
    def configure_kubernetes_client():
        """
        Configures the Kubernetes client for both in-cluster and local environments.
        """
        try:
            config.load_incluster_config()
            in_cluster = True
        except config.ConfigException:
            config.load_kube_config()
            in_cluster = False

        configuration = client.Configuration()

        if in_cluster:
            token_path = '/var/run/secrets/kubernetes.io/serviceaccount/token'
            with open(token_path, 'r') as f:
                token = f.read().strip()
            configuration.api_key['authorization'] = 'Bearer ' + token
            configuration.ssl_ca_cert = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
            configuration.host = 'https://kubernetes.default.svc'
        else:
            configuration = client.Configuration.get_default_copy()

        configuration.verify_ssl = True
        configuration.debug = False
        configuration.debugging = False

        return client.ApiClient(configuration)

    @staticmethod
    def create_service_account(name):
        """
        Creates a service account with the given name.
        """
        body = client.V1ServiceAccount(
            metadata=client.V1ObjectMeta(name=name),
            automount_service_account_token=True,
        )
        return body

    @staticmethod
    def create_service_account_token(name):
        """
        Creates a service account token for the given service account name.
        """
        body = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=name + "-token",
                annotations={"kubernetes.io/service-account.name": name}
            ),
            type="kubernetes.io/service-account-token"
        )
        return body
