## Deployment Guide for K8s IAM Operator

### Overview
This guide provides detailed instructions on how to deploy the K8s IAM Operator in a Kubernetes environment. The operator is designed to facilitate the creation, management, and monitoring of Kubernetes RBAC (Role-Based Access Control).

## Project Structure
The K8s IAM Operator project consists of the following structure:

```text
operator/
├── operator
│   ├── __init__.py        # Initialization script for the operator module
│   ├── handlers.py        # Handlers for various operator functionalities
│   ├── controllers.py     # Controllers to manage Kubernetes resources
│   └── utils.py           # Utility functions for the operator
├── config
│   ├── __init__.py        # Initialization script for configuration
│   ├── default.py         # Default configuration settings
│   └── production.py      # Production-specific configuration settings
├── crd
│   ├── group_crd.yaml     # Custom Resource Definition for groups
│   ├── roles_crd.yaml     # Custom Resource Definition for roles
│   └── user_crd.yaml      # Custom Resource Definition for users
├── tests
│   ├── __init__.py        # Initialization script for tests
│   ├── test_handlers.py   # Unit tests for handlers
│   └── test_controllers.py# Unit tests for controllers
├── setup.py               # Setup script for the project
├── setup.cfg              # Configuration file for setup
└── requirements.txt       # List of dependencies
```

## Deployment Steps

### 1. Deploying the Operator

To deploy the K8s IAM Operator as a pod in your Kubernetes cluster, use the following Kubernetes Deployment manifest.

```kubernetes
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k8s-iam-operator
spec:
  replicas: 1                       # Ensures a single instance of the operator
  selector:
    matchLabels:
      app: operator
  template:
    metadata:
      labels:
        app: operator
    spec:
      containers:
      - name: operator-container
        image: k8s-iam-operator:1.0.0 # Replace with the desired operator image version and repository
```

Apply the deployment using the command:

```shell
kubectl apply -f operator-deployment.yaml
```

### 2. Creating the CRDs

Before using the operator, you need to create the required Custom Resource Definitions (CRDs) in your Kubernetes cluster.

Execute the following commands to create the CRDs:

```shell
kubectl apply -f crd/group_crd.yaml
kubectl apply -f crd/roles_crd.yaml
kubectl apply -f crd/users_crd.yaml
```

These commands will set up the necessary CRDs (`group_crd.yaml`, `roles_crd.yaml`, `users_crd.yaml`) for the operator to function correctly.
