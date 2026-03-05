# Production Deployment Guide

This guide provides comprehensive instructions for deploying k8s-iam-operator in production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [HA Deployment Checklist](#ha-deployment-checklist)
- [Security Hardening](#security-hardening)
- [Monitoring Setup](#monitoring-setup)
- [Backup and Recovery](#backup-and-recovery)
- [Capacity Planning](#capacity-planning)
- [Maintenance Windows](#maintenance-windows)

## Prerequisites

Before deploying to production, ensure:

- [ ] Kubernetes 1.24+ cluster with sufficient capacity
- [ ] Helm 3.x installed
- [ ] kubectl configured with cluster admin access
- [ ] Container registry accessible from the cluster
- [ ] Monitoring stack (Prometheus/Grafana) deployed
- [ ] Network policies supported by CNI

## HA Deployment Checklist

### Minimum Requirements for HA

- [ ] **Multiple replicas**: At least 2 operator pods
- [ ] **Pod anti-affinity**: Spread across nodes
- [ ] **Pod Disruption Budget**: Ensure availability during updates
- [ ] **Resource requests/limits**: Properly sized

### Deploy with HA Configuration

```bash
helm upgrade --install k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  --create-namespace \
  -f charts/k8s-iam-operator/values-production.yaml
```

### Verify HA Setup

```bash
# Check pod distribution
kubectl get pods -n iam -o wide

# Verify PDB
kubectl get pdb -n iam

# Test failover
kubectl delete pod -n iam -l app.kubernetes.io/name=k8s-iam-operator --wait=false
kubectl get pods -n iam -w
```

### Production values.yaml Example

```yaml
replicaCount: 3

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 200m
    memory: 256Mi

podDisruptionBudget:
  enabled: true
  minAvailable: 2

affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app.kubernetes.io/name: k8s-iam-operator
        topologyKey: kubernetes.io/hostname

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 70
```

## Security Hardening

### Pod Security Standards

The operator runs with restricted Pod Security Standards:

```yaml
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

### Network Policies

Enable network policies to restrict traffic:

```yaml
networkPolicy:
  enabled: true
```

This creates a NetworkPolicy that:
- Allows ingress from Prometheus for metrics scraping
- Allows egress to Kubernetes API server
- Allows egress to tracing endpoint (if enabled)
- Denies all other traffic

### RBAC Best Practices

1. **Principle of least privilege**: The operator only requests necessary permissions
2. **Audit operator actions**: Enable audit logging (see [Audit & Compliance Guide](./audit.md))
3. **Review ClusterRole**: Periodically audit operator permissions

```bash
# Review operator permissions
kubectl get clusterrole k8s-iam-operator -o yaml
```

### Audit Logging

The operator provides built-in audit logging for IAM operations. For comprehensive user activity tracking, enable Kubernetes API server audit logging. See the [Audit & Compliance Guide](./audit.md) for:

- Operator audit log format and configuration
- Kubernetes API server audit setup
- Correlating IAM users with API activity
- Log aggregation recommendations

### Secret Management

- Use external secret management (Vault, AWS Secrets Manager) for sensitive data
- Rotate ServiceAccount tokens regularly
- Encrypt secrets at rest (enable etcd encryption)

### Image Security

- Use signed images from a trusted registry
- Scan images for vulnerabilities
- Pin image versions (avoid `:latest`)

```yaml
image:
  repository: quay.io/yannick_siewe/k8s-iam-operator
  pullPolicy: Always
  tag: "3.0.0"  # Pin specific version
```

## Monitoring Setup

### Enable ServiceMonitor

```yaml
serviceMonitor:
  enabled: true
  interval: 30s
  additionalLabels:
    release: prometheus
```

### Enable PrometheusRule

```yaml
prometheusRule:
  enabled: true
  additionalLabels:
    release: prometheus
```

### Enable Grafana Dashboard

```yaml
grafanaDashboard:
  enabled: true
  labels:
    grafana_dashboard: "1"
```

### Key Metrics to Monitor

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `up` | Operator availability | < 1 for 5m |
| `kopf_handler_errors_total` | Reconciliation errors | > 5/5m |
| `kopf_handler_duration_seconds` | Reconciliation latency | p99 > 30s |
| `container_memory_usage_bytes` | Memory usage | > 90% limit |
| `container_cpu_usage_seconds_total` | CPU usage | > 90% limit |

### Alerting Rules

The PrometheusRule includes alerts for:
- Operator down
- High error rate
- Slow reconciliation
- Resource exhaustion

See [runbooks](./runbooks/) for alert response procedures.

## Backup and Recovery

### What to Backup

1. **Custom Resources**: User, Group, Role CRs
2. **Helm values**: Production configuration
3. **Secrets**: If not using external secret management

### Backup Procedure

```bash
# Backup CRDs
kubectl get crd users.k8sio.auth -o yaml > backup/crd-users.yaml
kubectl get crd groups.k8sio.auth -o yaml > backup/crd-groups.yaml
kubectl get crd roles.k8sio.auth -o yaml > backup/crd-roles.yaml

# Backup all custom resources
kubectl get users.k8sio.auth -A -o yaml > backup/users.yaml
kubectl get groups.k8sio.auth -A -o yaml > backup/groups.yaml
kubectl get roles.k8sio.auth -A -o yaml > backup/roles.yaml

# Backup Helm values
helm get values k8s-iam-operator -n iam > backup/values.yaml
```

### Recovery Procedure

```bash
# 1. Install CRDs
kubectl apply -f backup/crd-users.yaml
kubectl apply -f backup/crd-groups.yaml
kubectl apply -f backup/crd-roles.yaml

# 2. Deploy operator
helm upgrade --install k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  --create-namespace \
  -f backup/values.yaml

# 3. Restore resources
kubectl apply -f backup/users.yaml
kubectl apply -f backup/groups.yaml
kubectl apply -f backup/roles.yaml
```

### Disaster Recovery Testing

Test recovery procedures quarterly:

1. Create test resources
2. Perform backup
3. Delete resources
4. Restore from backup
5. Verify functionality

## Capacity Planning

### Resource Sizing

| Managed Resources | Replicas | CPU Request | Memory Request |
|-------------------|----------|-------------|----------------|
| < 100 | 2 | 100m | 128Mi |
| 100-500 | 2-3 | 200m | 256Mi |
| 500-1000 | 3-5 | 500m | 512Mi |
| > 1000 | 5+ | 1000m | 1Gi |

### Scaling Considerations

- **Horizontal scaling**: Use HPA for automatic scaling
- **Vertical scaling**: Increase resources for large reconciliation batches
- **API rate limiting**: Consider Kubernetes API server capacity

### Performance Testing

Before production deployment:

```bash
# Create test load
for i in $(seq 1 100); do
  cat <<EOF | kubectl apply -f -
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: test-user-$i
spec:
  roleRef: viewer
  namespaces:
    - default
EOF
done

# Monitor reconciliation
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator -f
```

## Maintenance Windows

### Planned Maintenance

1. **Notify stakeholders** in advance
2. **Scale up replicas** before maintenance
3. **Perform rolling updates**
4. **Monitor during and after**

### Update Procedure

```bash
# 1. Check current version
helm list -n iam

# 2. Review changes
helm diff upgrade k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  -f values-production.yaml

# 3. Perform update
helm upgrade k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  -f values-production.yaml

# 4. Monitor rollout
kubectl rollout status deployment -n iam k8s-iam-operator

# 5. Verify functionality
kubectl get users.k8sio.auth -A
```

### Rollback Procedure

```bash
# List revisions
helm history k8s-iam-operator -n iam

# Rollback to previous version
helm rollback k8s-iam-operator <revision> -n iam
```

## Pre-Production Checklist

- [ ] HA configuration verified
- [ ] Pod anti-affinity configured
- [ ] PDB enabled
- [ ] Network policies enabled
- [ ] Resource limits set
- [ ] ServiceMonitor enabled
- [ ] PrometheusRule enabled
- [ ] Grafana dashboard deployed
- [ ] Alerts tested
- [ ] Backup procedure tested
- [ ] Recovery procedure tested
- [ ] Runbooks reviewed
- [ ] On-call rotation established
