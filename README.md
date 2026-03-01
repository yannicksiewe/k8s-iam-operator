# k8s-iam-operator

A production-ready Kubernetes operator for IAM management using Custom Resource Definitions (CRDs).

[![CI](https://github.com/yannick-siewe/k8s-iam-operator/workflows/CI/badge.svg)](https://github.com/yannick-siewe/k8s-iam-operator/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

The k8s-iam-operator streamlines Kubernetes Role-Based Access Control (RBAC) management by providing custom resources for Users, Groups, and Roles. It automates ServiceAccount creation, RBAC bindings, and kubeconfig generation.

## Features

- **User Management**: Create ServiceAccounts with automatic RBAC bindings
- **Group Management**: Define group-based access control
- **Role Management**: Define custom Roles and ClusterRoles via CRDs
- **Kubeconfig Generation**: Automatic kubeconfig secrets for enabled users
- **Namespace Isolation**: Optional dedicated namespace per user
- **Audit Logging**: Structured JSON audit logs for compliance
- **Observability**: Prometheus metrics and OpenTelemetry tracing

## Quick Start

### Prerequisites

- Kubernetes 1.24+
- Helm 3.x

### Installation

```bash
# Install with Helm
helm upgrade --install k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  --create-namespace
```

### Create a User

```yaml
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: developer
  namespace: iam
spec:
  enabled: true
  CRoles:
    - namespace: dev
      clusterRole: edit
    - namespace: staging
      clusterRole: view
```

```bash
kubectl apply -f user.yaml
```

### Create a Group

```yaml
apiVersion: k8sio.auth/v1
kind: Group
metadata:
  name: devops
  namespace: iam
spec:
  CRoles:
    - namespace: production
      clusterRole: view
    - clusterRole: cluster-view  # Cluster-wide
```

```bash
kubectl apply -f group.yaml
```

## Documentation

- [Deployment Guide](docs/deployment.md)
- [API Reference](docs/api-reference.md)
- [Development Guide](docs/development.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

## Architecture

```
┌─────────────────────────────────────────────┐
│            Kopf Event Handlers              │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│     Service Layer (Business Logic)          │
│  UserService │ GroupService │ RoleService   │
│         RBACService │ KubeconfigService     │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│    Repository Layer (K8s API Abstraction)   │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│            Kubernetes API                    │
└─────────────────────────────────────────────┘
```

## Development

```bash
# Install dependencies
make install-deps

# Run linting
make lint

# Run unit tests
make test

# Run with coverage
make test-coverage

# Build Docker image
make build

# Run locally
make run
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `GROUP_NAME` | CRD API group | `k8sio.auth` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENABLE_TRACING` | Enable OpenTelemetry | `False` |
| `TEMPO_ENDPOINT` | OTLP endpoint | `http://localhost:4317/` |
| `AUDIT_ENABLED` | Enable audit logging | `True` |

## Helm Values

See [values.yaml](charts/k8s-iam-operator/values.yaml) for all options.

Key settings:
- `replicaCount`: Number of replicas
- `resources`: CPU/memory limits
- `tracing.enabled`: Enable distributed tracing
- `networkPolicy.enabled`: Enable network restrictions
- `podDisruptionBudget.enabled`: Enable PDB for HA

## License

MIT License - see [LICENSE](LICENSE.md)

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## Acknowledgments

Built with:
- [Kopf](https://kopf.readthedocs.io/) - Kubernetes Operator Framework for Python
- [Flask](https://flask.palletsprojects.com/) - Health/metrics endpoints
- [OpenTelemetry](https://opentelemetry.io/) - Distributed tracing
