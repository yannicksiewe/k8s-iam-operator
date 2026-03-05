# k8s-iam-operator

A production-ready Kubernetes operator for IAM management using Custom Resource Definitions (CRDs).

[![CI](https://github.com/yannicksiewe/k8s-iam-operator/workflows/CI/badge.svg)](https://github.com/yannicksiewe/k8s-iam-operator/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

The k8s-iam-operator streamlines Kubernetes Role-Based Access Control (RBAC) management by providing custom resources for Users, Groups, and Roles. It automates ServiceAccount creation, RBAC bindings, and kubeconfig generation.

## Features

- **User Management**: Create human users or service accounts with automatic RBAC
- **User Types**:
  - `human` - Dedicated namespace + kubeconfig for interactive access
  - `serviceAccount` - SA in target namespace for workload identity
- **Namespace Isolation**: Optional quotas and network policies per user
- **Group Management**: Define group-based access control
- **Role Management**: Define custom Roles and ClusterRoles via CRDs
- **Kubeconfig Generation**: Automatic kubeconfig secrets for human users
- **Audit Logging**: Structured JSON audit logs with event categories
- **Observability**: Prometheus metrics and OpenTelemetry tracing

## Quick Start

### Prerequisites

- Kubernetes 1.24+
- Helm 3.10+

### Installation

```bash
helm install k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  --create-namespace
```

## User Types

### Human User

Creates a dedicated namespace with kubeconfig for interactive cluster access.

```yaml
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: alice
  namespace: iam
spec:
  type: human
  namespaceConfig:
    labels:
      team: backend
    quota:
      cpu: "4"
      memory: "8Gi"
      pods: "20"
    networkPolicy: isolated  # none | isolated | restricted
  CRoles:
    - namespace: development
      clusterRole: edit
    - namespace: staging
      clusterRole: view
```

**Creates:**
- ServiceAccount `alice` in `iam` namespace
- Namespace `alice` with quota and network policy
- Kubeconfig secret `alice-cluster-config` in `alice` namespace
- RoleBindings for specified roles

### ServiceAccount User

Creates a ServiceAccount for applications/workloads.

```yaml
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: backend-api
  namespace: iam
spec:
  type: serviceAccount
  targetNamespace: production  # Where to create the SA
  CRoles:
    - namespace: production
      clusterRole: view
```

**Creates:**
- ServiceAccount `backend-api` in `production` namespace
- RoleBindings for specified roles

## Group Management

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

## Namespace Isolation Options

For human users, configure namespace security:

```yaml
spec:
  type: human
  namespaceConfig:
    # Custom labels and annotations
    labels:
      cost-center: engineering
      environment: dev
    annotations:
      description: "Developer workspace"

    # Resource quotas
    quota:
      cpu: "4"              # Total CPU limit
      memory: "8Gi"         # Total memory limit
      pods: "20"            # Max pods
      services: "10"        # Max services
      persistentvolumeclaims: "5"

    # Network isolation
    networkPolicy: isolated   # Options:
                              # - none: No restrictions (default)
                              # - isolated: Allow only same-namespace traffic
                              # - restricted: Deny all except DNS and same namespace
```

## Documentation

- [Architecture](docs/architecture.md)
- [Production Guide](docs/production-guide.md)
- [Audit & Compliance](docs/audit.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Upgrade Guide](docs/upgrade-guide.md)
- [SLO Documentation](docs/slo.md)
- [ESO Integration](docs/integrations/external-secrets-operator.md)

### Runbooks

- [Operator Down](docs/runbooks/operator-down.md)
- [High Error Rate](docs/runbooks/high-error-rate.md)
- [Reconciliation Stuck](docs/runbooks/reconciliation-stuck.md)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     k8s-iam-operator                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                  Kopf Event Handlers                         │  │
│   │   UserHandler │ GroupHandler │ RoleHandler                   │  │
│   └─────────────────────────┬───────────────────────────────────┘  │
│                             │                                      │
│   ┌─────────────────────────▼───────────────────────────────────┐  │
│   │              Service Layer (Business Logic)                  │  │
│   │                                                              │  │
│   │  UserService ─────► RBACService ─────► KubeconfigService    │  │
│   │       │                  │                                   │  │
│   │       ▼                  ▼                                   │  │
│   │  GroupService      RoleService                               │  │
│   └─────────────────────────┬───────────────────────────────────┘  │
│                             │                                      │
│   ┌─────────────────────────▼───────────────────────────────────┐  │
│   │           Repository Layer (K8s API Abstraction)            │  │
│   │                                                              │  │
│   │  ServiceAccountRepo │ NamespaceRepo │ SecretRepo            │  │
│   │  RBACRepo │ ResourceQuotaRepo │ NetworkPolicyRepo           │  │
│   └─────────────────────────┬───────────────────────────────────┘  │
│                             │                                      │
│                             ▼                                      │
│                     Kubernetes API                                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Metrics

The operator exposes Prometheus metrics at `/metrics`:

| Metric | Description |
|--------|-------------|
| `k8s_iam_operator_users_created_total` | Users created by type |
| `k8s_iam_operator_users_total` | Current user count |
| `k8s_iam_operator_role_bindings_created_total` | RBAC bindings created |
| `k8s_iam_operator_handler_duration_seconds` | Handler execution time |
| `k8s_iam_operator_handler_errors_total` | Handler errors |
| `k8s_iam_operator_namespaces_created_total` | User namespaces created |
| `k8s_iam_operator_kubeconfigs_generated_total` | Kubeconfigs generated |

## Development

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run linting
flake8 app/ tests/

# Run tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
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

```yaml
replicaCount: 2

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi

# Enable HPA
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5

# Enable Prometheus alerts
prometheusRule:
  enabled: true

# Enable Grafana dashboard
grafanaDashboard:
  enabled: true
```

## License

MIT License - see [LICENSE](LICENSE.md)

## Contributing

Contributions are welcome! Please read the contribution guidelines first.

## Acknowledgments

Built with:
- [Kopf](https://kopf.readthedocs.io/) - Kubernetes Operator Framework for Python
- [Flask](https://flask.palletsprojects.com/) - Health/metrics endpoints
- [OpenTelemetry](https://opentelemetry.io/) - Distributed tracing
