# Upgrade Guide

This guide covers upgrading k8s-iam-operator between versions.

## Table of Contents

- [Before You Upgrade](#before-you-upgrade)
- [Version Compatibility](#version-compatibility)
- [Upgrade Procedures](#upgrade-procedures)
- [Breaking Changes](#breaking-changes)
- [Rollback Procedures](#rollback-procedures)

## Before You Upgrade

### Pre-Upgrade Checklist

- [ ] Read the release notes for target version
- [ ] Check version compatibility matrix below
- [ ] Backup all custom resources
- [ ] Verify current deployment is healthy
- [ ] Schedule maintenance window (if needed)
- [ ] Notify affected users

### Backup Current State

```bash
# Create backup directory
mkdir -p backup-$(date +%Y%m%d)
cd backup-$(date +%Y%m%d)

# Backup Helm release values
helm get values k8s-iam-operator -n iam > values-backup.yaml

# Backup CRDs
kubectl get crd users.k8sio.auth -o yaml > crd-users.yaml
kubectl get crd groups.k8sio.auth -o yaml > crd-groups.yaml
kubectl get crd roles.k8sio.auth -o yaml > crd-roles.yaml

# Backup all custom resources
kubectl get users.k8sio.auth -A -o yaml > users.yaml
kubectl get groups.k8sio.auth -A -o yaml > groups.yaml
kubectl get roles.k8sio.auth -A -o yaml > roles.yaml

# Record current version
helm list -n iam > helm-status.txt
```

### Verify Current Health

```bash
# Check operator status
kubectl get pods -n iam

# Check for pending resources
kubectl get users.k8sio.auth -A | grep -v "Ready\|Completed"

# Check operator logs for errors
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --tail=50 | grep -i error
```

## Version Compatibility

### Kubernetes Compatibility

| Operator Version | Minimum K8s | Maximum K8s | Notes |
|-----------------|-------------|-------------|-------|
| 3.0.x | 1.24 | 1.29 | Current stable |
| 2.x.x | 1.22 | 1.27 | Legacy |
| 1.x.x | 1.20 | 1.25 | Deprecated |

### Helm Compatibility

| Operator Version | Minimum Helm | Notes |
|-----------------|--------------|-------|
| 3.0.x | 3.10.0 | |
| 2.x.x | 3.8.0 | |
| 1.x.x | 3.0.0 | |

### CRD API Versions

| Operator Version | CRD API Version | Notes |
|-----------------|-----------------|-------|
| 3.0.x | v1 | Current |
| 2.x.x | v1 | |
| 1.x.x | v1beta1 | Deprecated |

## Upgrade Procedures

### Standard Upgrade (Minor/Patch Versions)

For upgrades within the same major version (e.g., 3.0.0 → 3.1.0):

```bash
# 1. Pull latest chart
git pull origin main

# 2. Review changes
helm diff upgrade k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  -f your-values.yaml

# 3. Perform upgrade
helm upgrade k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  -f your-values.yaml

# 4. Monitor rollout
kubectl rollout status deployment -n iam k8s-iam-operator

# 5. Verify health
kubectl get pods -n iam
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --tail=20
```

### Major Version Upgrade (e.g., 2.x → 3.x)

Major upgrades may include breaking changes. Follow these steps carefully:

```bash
# 1. Read breaking changes section below

# 2. Scale to single replica for safer upgrade
kubectl scale deployment -n iam k8s-iam-operator --replicas=1

# 3. Wait for scale down
kubectl wait --for=condition=available deployment/k8s-iam-operator -n iam

# 4. Apply CRD updates first
kubectl apply -f crd/

# 5. Verify CRDs
kubectl get crd | grep k8sio.auth

# 6. Perform Helm upgrade
helm upgrade k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  -f your-values.yaml

# 7. Monitor upgrade
kubectl rollout status deployment -n iam k8s-iam-operator

# 8. Scale back up
kubectl scale deployment -n iam k8s-iam-operator --replicas=2

# 9. Run migration scripts (if any)
# See breaking changes section

# 10. Verify all resources
kubectl get users.k8sio.auth -A
kubectl get groups.k8sio.auth -A
```

### Zero-Downtime Upgrade

For production environments requiring zero downtime:

```bash
# 1. Ensure PDB is configured
kubectl get pdb -n iam

# 2. Scale up before upgrade
kubectl scale deployment -n iam k8s-iam-operator --replicas=3

# 3. Perform rolling upgrade
helm upgrade k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  -f your-values.yaml \
  --set deployment.strategy.type=RollingUpdate \
  --set deployment.strategy.rollingUpdate.maxUnavailable=1 \
  --set deployment.strategy.rollingUpdate.maxSurge=1

# 4. Monitor pods
kubectl get pods -n iam -w

# 5. Scale back to normal
kubectl scale deployment -n iam k8s-iam-operator --replicas=2
```

## Breaking Changes

### Version 3.0.0

**CRD Changes:**
- Added `status.conditions` field to all CRDs
- Renamed `spec.role` to `spec.roleRef` in User CRD

**Migration Steps:**
```bash
# Update existing User resources
kubectl get users.k8sio.auth -A -o json | \
  jq '.items[] | select(.spec.role) | .metadata.name' | \
  xargs -I {} kubectl patch users.k8sio.auth {} --type=json \
    -p='[{"op": "move", "from": "/spec/role", "path": "/spec/roleRef"}]'
```

**Configuration Changes:**
- `tracing.jaegerEndpoint` replaced with `tracing.endpoint`
- Default port changed from 8080 to 8081

**Helm Values Migration:**
```yaml
# Old (2.x)
tracing:
  jaegerEndpoint: "http://jaeger:14268/api/traces"

# New (3.x)
tracing:
  endpoint: "http://tempo:4317/"
```

### Version 2.0.0

**CRD Changes:**
- API version changed from `v1beta1` to `v1`
- `spec.permissions` renamed to `spec.rules`

**Migration Steps:**
```bash
# Export resources in old format
kubectl get users.k8sio.auth -A -o yaml > users-v1beta1.yaml

# Convert to new format (manual or script)
# Apply CRD updates
kubectl apply -f crd/

# Re-apply converted resources
kubectl apply -f users-v1.yaml
```

## Rollback Procedures

### Quick Rollback

If issues are detected immediately after upgrade:

```bash
# 1. Check Helm history
helm history k8s-iam-operator -n iam

# 2. Rollback to previous revision
helm rollback k8s-iam-operator <previous-revision> -n iam

# 3. Verify rollback
kubectl get pods -n iam
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --tail=20
```

### CRD Rollback

If CRD changes cause issues:

```bash
# 1. Restore CRDs from backup
kubectl apply -f backup-YYYYMMDD/crd-users.yaml
kubectl apply -f backup-YYYYMMDD/crd-groups.yaml
kubectl apply -f backup-YYYYMMDD/crd-roles.yaml

# 2. Rollback Helm release
helm rollback k8s-iam-operator <previous-revision> -n iam

# 3. If resources were modified, restore from backup
kubectl apply -f backup-YYYYMMDD/users.yaml
kubectl apply -f backup-YYYYMMDD/groups.yaml
```

### Full Disaster Recovery

If upgrade causes severe issues:

```bash
# 1. Uninstall current release
helm uninstall k8s-iam-operator -n iam

# 2. Delete CRDs (this will delete all resources!)
kubectl delete crd users.k8sio.auth groups.k8sio.auth roles.k8sio.auth

# 3. Re-apply old CRDs
kubectl apply -f backup-YYYYMMDD/crd-users.yaml
kubectl apply -f backup-YYYYMMDD/crd-groups.yaml
kubectl apply -f backup-YYYYMMDD/crd-roles.yaml

# 4. Reinstall previous version
helm install k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  -f backup-YYYYMMDD/values-backup.yaml \
  --version <previous-version>

# 5. Restore resources
kubectl apply -f backup-YYYYMMDD/users.yaml
kubectl apply -f backup-YYYYMMDD/groups.yaml
kubectl apply -f backup-YYYYMMDD/roles.yaml
```

## Post-Upgrade Verification

### Verification Checklist

- [ ] All operator pods running
- [ ] No error logs
- [ ] Metrics endpoint accessible
- [ ] All resources in Ready state
- [ ] Test user creation works
- [ ] Existing users can authenticate

### Verification Commands

```bash
# 1. Pod health
kubectl get pods -n iam

# 2. Logs clean
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --since=5m | grep -i error

# 3. Metrics available
kubectl port-forward -n iam svc/k8s-iam-operator 8081:8081 &
curl http://localhost:8081/actuator/metrics | head

# 4. Resources healthy
kubectl get users.k8sio.auth -A
kubectl get groups.k8sio.auth -A

# 5. Test reconciliation
kubectl apply -f - <<EOF
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: upgrade-test
spec:
  roleRef: viewer
  namespaces:
    - default
EOF

kubectl get users.k8sio.auth upgrade-test -o yaml
kubectl delete users.k8sio.auth upgrade-test
```

## Getting Help

If you encounter issues during upgrade:

1. Check [Troubleshooting Guide](./troubleshooting.md)
2. Review [Runbooks](./runbooks/)
3. Open an issue at https://github.com/yannick-siewe/k8s-iam-operator/issues
