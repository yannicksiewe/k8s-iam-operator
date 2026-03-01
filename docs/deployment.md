# Deployment Guide

This guide covers deploying k8s-iam-operator to a Kubernetes cluster.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.x
- kubectl configured to access your cluster
- Cluster admin permissions

## Installation Methods

### Method 1: Helm Chart (Recommended)

```bash
# Add the Helm repository (if hosted)
# helm repo add k8s-iam https://charts.example.com
# helm repo update

# Install from local chart
helm upgrade --install k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  --create-namespace
```

#### Configuration

Create a custom values file for your environment:

```yaml
# values-custom.yaml
replicaCount: 2

config:
  logLevel: "INFO"

tracing:
  enabled: true
  endpoint: "http://tempo.monitoring:4317/"

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 200m
    memory: 256Mi

podDisruptionBudget:
  enabled: true
  minAvailable: 1
```

Install with custom values:

```bash
helm upgrade --install k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  --create-namespace \
  -f values-custom.yaml
```

### Method 2: Raw Kubernetes Manifests

```bash
# Install CRDs
kubectl apply -f crd/

# Create namespace
kubectl create namespace iam

# Install RBAC
kubectl apply -f crd/rbac.yaml

# Install deployment
kubectl apply -f deployment.yaml
```

## Verification

Check that the operator is running:

```bash
kubectl get pods -n iam
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator
```

Verify CRDs are installed:

```bash
kubectl get crd | grep k8sio.auth
```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROUP_NAME` | CRD API group | `k8sio.auth` |
| `VERSION` | CRD API version | `v1` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENABLE_TRACING` | Enable OpenTelemetry | `False` |
| `TEMPO_ENDPOINT` | OTLP endpoint | `http://localhost:4317/` |
| `AUDIT_ENABLED` | Enable audit logging | `True` |

### Helm Values

See `charts/k8s-iam-operator/values.yaml` for all configurable options.

Key settings:

- `replicaCount`: Number of operator replicas
- `resources`: CPU/memory limits
- `tracing.enabled`: Enable distributed tracing
- `networkPolicy.enabled`: Enable network restrictions
- `podDisruptionBudget.enabled`: Enable PDB for HA

## Production Recommendations

1. **High Availability**: Run 2+ replicas with PDB
2. **Resource Limits**: Set appropriate limits
3. **Network Policy**: Enable to restrict traffic
4. **Monitoring**: Enable ServiceMonitor for Prometheus
5. **Tracing**: Enable for debugging
6. **Audit Logs**: Keep enabled for compliance

Use production values:

```bash
helm upgrade --install k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  --create-namespace \
  -f charts/k8s-iam-operator/values-production.yaml
```

## Upgrading

```bash
# Update Helm chart
helm upgrade k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  --reuse-values
```

## Uninstalling

```bash
# Uninstall via Helm
helm uninstall k8s-iam-operator --namespace iam

# Delete namespace
kubectl delete namespace iam

# Optionally delete CRDs (will delete all User/Group/Role resources!)
kubectl delete -f crd/
```

## Troubleshooting

### Operator not starting

Check logs:
```bash
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator
```

Check RBAC:
```bash
kubectl auth can-i --list --as=system:serviceaccount:iam:k8s-iam-operator
```

### Resources not being processed

Check operator logs for errors:
```bash
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --tail=100
```

Verify CRDs:
```bash
kubectl get users.k8sio.auth -A
kubectl get groups.k8sio.auth -A
```
