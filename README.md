### SSH Public Key:
### ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCq8xmXKlHLvM3EZbAEfkaUpx1KtGvyk90WoXKBLGRxBxPQg3CwwHj2VLo7Lgwvjgb07se6XGDF4bEo6kSGXlPaDc6Kz+La7qDEywALJB6mLJNINu0erWqjs9+QabZyc/ouWrc1lTc269HiE6vLfORSoZKt1q8lYXX7HYLRQiqEzMzMswuNDnHQzl2NLMKwgAxWoaKRkV1+aaiae3OBJDxpuwgSoychG8I7w7SBSg2XQdAkJGFueMN9vIR8TxbMJsgGWz4ILd2HVK5JR4Ks8zFFK1ZTpnoJHFx7TETRNxldMNSKkElTohTWRSdPTlgKvERAUmaIKrtHwteXsnuGMYFj

# K8s-iam-operator
A Python-based Kubernetes Operator using the Kopf library to manage Roles, ClusterRoles, Groups, and Users.

### Table of Contents
- Permissions matrix
- Project Structure 
- Deployment
- Usage
- Source


### User Permissions matrix
|ClusterRole.    | 	 get     |    list   |   watch   |  create   |   update  |    patch  |   delete  |
|:---------------|:----------|:----------|:----------|:----------|:----------|:----------|:----------|
| observer       |      ✓    |      ✓    |      ✓    |     ✘     |      ✘    |      ✘    |      ✘    |
| admin          |      ✓    |      ✓    |      ✓    |     ✓     |      ✓    |      ✓    |      ✓    |
| developer      |      ✓    |      ✓    |      ✓    |     ✓     |      ✓    |      ✓    |      ✓    |
| namespace-list |      ✓    |      ✓    |      ✘    |     ✘     |      ✘    |      ✘    |      ✘    |

| group     | dev       | test      | prod      |
|:----------|:----------|:----------|:----------|
| developer |     ✓     |     ✓     |     ✘     |
| observer  |     ✓     |     ✓     |     ✓     |
| admin     |     ✓     |     ✓     |     ✓     |

|resources         | admin     | developer | observer  | namespace-list|
|:-----------------|:----------|:----------|:----------|:--------------|
| pods             |     ✓     |     ✓     |     ✓     |       ✘       |
| pods/logs        |     ✓     |     ✓     |     ✘     |       ✘       |
| pods/portforward |     ✓     |     ✓     |     ✘     |       ✘       |
| services         |     ✓     |     ✓     |     ✓     |       ✘       |
| ingresses        |     ✓     |     ✓     |     ✓     |       ✘       |
| deployments      |     ✓     |     ✓     |     ✓     |       ✘       |
| DaemonSets       |     ✓     |     ✓     |     ✓     |       ✘       |
| StatefulSets     |     ✓     |     ✓     |     ✓     |       ✘       |
| ReplicaSets      |     ✓     |     ✓     |     ✘     |       ✘       |
| CronJobs         |     ✓     |     ✓     |     ✓     |       ✘       |
| Jobs             |     ✓     |     ✓     |     ✓     |       ✘       |
| secrets          |     ✓     |     ✓     |     ✘     |       ✘       |
| configmaps       |     ✓     |     ✓     |     ✓     |       ✘       |
| PVC              |     ✓     |     ✓     |     ✘     |       ✘       |
| PV               |     ✓     |     ✓     |     ✘     |       ✘       |
| Namespace        |     ✓     |     ✘     |     ✘     |       ✓       |


### Project Structure 
operator/
```text
├── operator
│   ├── __init__.py
│   ├── handlers.py
│   ├── controllers.py
│   └── utils.py
├── config
│   ├── __init__.py
│   ├── default.py
│   └── production.py
├── crd
│   ├── group_crd.yaml
│   ├── roles_crd.yaml
│   └── user_crd.yaml
├── tests
│   ├── __init__.py
│   ├── test_handlers.py
│   └── test_controllers.py
├── setup.py
├── setup.cfg
└── requirements.txt
```

### Deployment
To deploy this operator as a pod in Kubernetes, you typically create a Deployment manifest. 
Here's an example to illustrate the process: 
```kubernetes
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k8s-iam-operator
spec:
  template:
    metadata:
      labels:
        app: operator
    spec:
      containers:
      - name: operator-container
        image: k8s-iam-operator:1.0.0
```
```shell
kubectl apply -f operator-deployment.yaml
```

### Usage
To use the operator follow these steps:
1. Create the [CRDs](k8s-iam-operator/crd/):
```shell
kubectl apply -f crd/rbac.yaml
kubectl apply -f crd/group_crd.yaml
kubectl apply -f crd/roles_crd.yaml
kubectl apply -f crd/users_crd.yaml
```
2. Create a user:
```kubernetes
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: tom
  namespace: iam
spec:
  enabled: true
  CRoles:
  - namespace: tom
    clusterRole: namespace-admin
```

The following actions have been performed when created user:

- Created a user named "tom" as a ServiceAccount in the "iam" namespace.
- Verified that user "tom" is enabled.
- Created a namespace named "tom" specifically for user "tom".
- Granted user "tom" namespace admin permissions for the "tom" namespace.
- Generated a kubeconfig file for user "tom".
- Saved the kubeconfig file in a secret within the "tom" namespace.

This enables user "tom" to access the kubeconfig file whenever needed.
These steps ensure that user "tom" has the necessary permissions and resources to work within their dedicated namespace.

### Source:
1. Implementing Kubernetes Operators with Python - Opcito. [https://www.opcito.com/blogs/implementing-kubernetes-operators-with-python.](url)
2. Build a Kubernetes Operator in six steps | Red Hat Developer. [https://developers.redhat.com/articles/2021/09/07/build-kubernetes-operator-six-steps.](url)
3. Kubernetes Operators with Python - Spectro Cloud. [https://www.spectrocloud.com/blog/writing-kubernetes-operators-with-python/.](url)
