import base64
import json
from kubernetes import client, config


# Load the Kubernetes configuration from the default location
config.load_kube_config()


# def generate_cluster_config(spec, meta, **kwargs):
def generate_cluster_config(body):
    # Retrieve the service account token for the user
    sa_api = client.CoreV1Api()
    user_name = body['metadata']['name']
    user_namespace = body['metadata']['namespace']
    url_api = sa_api.api_client

    # Retrieve User token information
    secrets = sa_api.list_namespaced_secret(namespace=user_namespace)
    token_secret = next((s for s in secrets.items if s.metadata.name.startswith(user_name)), None)
    token = token_secret.data['token']

    # Retrieve the cluster information from the configuration
    config_map = sa_api.read_namespaced_config_map(name='kube-root-ca.crt', namespace='kube-system')
    cluster_url = url_api.configuration.host
    cluster_ca = config_map.data['ca.crt']

    # Generate the cluster configuration data as a dictionary
    data = {
        'apiVersion': 'v1',
        'clusters': [{
            'cluster': {
                'server': cluster_url,
                'certificate-authority-data': base64.b64encode(cluster_ca.encode('utf-8')).decode('utf-8'),
            },
            'name': 'cluster',
        }],
        'contexts': [{
            'context': {
                'cluster': 'cluster',
                'user': f'{user_name}',
            },
            'name': f'{user_name}-context',
        }],
        'current-context': f'{user_name}-context',
        'users': [{
            'name': user_name,
            'user': {
                'token': base64.b64decode(token.encode('utf-8')).decode('utf-8'),
            },
        }],
    }

    # Create the secret containing the cluster configuration data
    secret_name = f'{user_name}-cluster-config'
    secret = client.V1Secret(
        metadata=client.V1ObjectMeta(name=secret_name),
        type='kubernetes.io/kubeconfig',
        data={
            'kubeconfig': base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')
        }
    )
    secret_api = client.CoreV1Api()
    secret_api.create_namespaced_secret(namespace=user_name, body=secret)

    return
