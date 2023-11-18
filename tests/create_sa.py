import base64

import kubernetes.client
from kubernetes.client.rest import ApiException
import kubernetes.config

# Load the kubeconfig file from the default location
kubernetes.config.load_kube_config()

# Load the kubeconfig file from a specific location
kubernetes.config.load_kube_config(config_file="~/.kube/config")


def create_service_account(name, namespace):
    # Create a Kubernetes client
    client = kubernetes.client.CoreV1Api()

    # Create a service account object
    body = kubernetes.client.V1ServiceAccount(metadata=kubernetes.client.V1ObjectMeta(name=name))

    # Create the service account
    try:
        client.create_namespaced_service_account(namespace, body)
        print(f"Service account {name} created in namespace {namespace}")
    except ApiException as e:
        print(f"Failed to create service account: {e}")


def create_service_account_token(name, namespace):
    # Create a Kubernetes client
    client = kubernetes.client.CoreV1Api()

    # Create a secret object
    body = kubernetes.client.V1Secret(
        metadata=kubernetes.client.V1ObjectMeta(
            name=name,
            annotations={
                "kubernetes.io/service-account.name": name
            }
        ),
        type="kubernetes.io/service-account-token"
    )

    # Create the secret
    try:
        client.create_namespaced_secret(namespace, body)
        print(f"Service account token {name} created in namespace {namespace}")
    except ApiException as e:
        print(f"Failed to create service account token: {e}")


def get_service_account_token(name, namespace):
    # Create a Kubernetes client
    client = kubernetes.client.CoreV1Api()

    # Get the secret
    try:
        secret = client.read_namespaced_secret(name, namespace)
        token = base64.b64decode(secret.data["token"]).decode("utf-8")
        print(f"Service account token: {token}")
    except ApiException as e:
        print(f"Failed to get service account token: {e}")


if __name__ == "__main__":
    service_account_name = "test-sa"
    namespace = "default"

    create_service_account(service_account_name, namespace)
    create_service_account_token(service_account_name, namespace)
    get_service_account_token(service_account_name, namespace)
