# Runbook: Operator Down

**Alert Name:** `IAMOperatorDown`
**Severity:** Critical
**Service:** k8s-iam-operator

## Overview

This runbook addresses the situation where the k8s-iam-operator is unavailable.

## Impact

- New User/Group/Role resources will not be processed
- Changes to existing resources will not be reconciled
- Kubeconfig generation will fail
- RBAC bindings will not be created/updated

**User Impact:** Users cannot be provisioned or have their access modified.

## Alert Definition

```yaml
alert: IAMOperatorDown
expr: absent(up{job="k8s-iam-operator"}) == 1
for: 5m
```

## Diagnosis Steps

### 1. Check Pod Status

```bash
kubectl get pods -n iam -l app.kubernetes.io/name=k8s-iam-operator
```

Possible states:
- **Pending**: Scheduling issues
- **CrashLoopBackOff**: Application crash
- **ImagePullBackOff**: Image not accessible
- **Running** but unhealthy: Health check failing

### 2. Check Events

```bash
kubectl get events -n iam --sort-by='.lastTimestamp' | head -20
```

### 3. Check Pod Logs

```bash
# Current logs
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --tail=100

# Previous container logs (if crashing)
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --previous
```

### 4. Check Node Status

```bash
# Get node where pod should be scheduled
kubectl get nodes

# Check node conditions
kubectl describe nodes | grep -A5 Conditions
```

### 5. Check Resource Availability

```bash
kubectl describe nodes | grep -A5 "Allocated resources"
```

## Resolution Steps

### Scenario 1: Pod in CrashLoopBackOff

1. **Check logs for error:**
   ```bash
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --previous
   ```

2. **Common causes:**
   - Missing CRDs: `kubectl apply -f crd/`
   - Invalid configuration: Check ConfigMap
   - RBAC issues: Check ClusterRole/ClusterRoleBinding

3. **Restart deployment:**
   ```bash
   kubectl rollout restart deployment -n iam k8s-iam-operator
   ```

### Scenario 2: Pod in Pending State

1. **Check events for scheduling issues:**
   ```bash
   kubectl describe pod -n iam -l app.kubernetes.io/name=k8s-iam-operator
   ```

2. **Common causes:**
   - Insufficient resources: Scale up cluster or reduce requests
   - Node selector mismatch: Check nodeSelector in values
   - Taint/Toleration issues: Add tolerations

3. **Verify PodDisruptionBudget:**
   ```bash
   kubectl get pdb -n iam
   ```

### Scenario 3: ImagePullBackOff

1. **Check image availability:**
   ```bash
   kubectl describe pod -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -A10 Events
   ```

2. **Verify image exists:**
   ```bash
   docker pull quay.io/yannick_siewe/k8s-iam-operator:latest
   ```

3. **Check imagePullSecrets:**
   ```bash
   kubectl get secrets -n iam | grep -i pull
   ```

### Scenario 4: Running but Unhealthy

1. **Check health endpoints:**
   ```bash
   kubectl port-forward -n iam svc/k8s-iam-operator 8081:8081 &
   curl http://localhost:8081/actuator/health
   ```

2. **Check liveness/readiness probes:**
   ```bash
   kubectl describe pod -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -A10 Liveness
   ```

3. **Increase probe timeouts if needed:**
   ```yaml
   livenessProbe:
     initialDelaySeconds: 60
     timeoutSeconds: 10
   ```

## Recovery Verification

1. **Verify pods are running:**
   ```bash
   kubectl get pods -n iam
   ```

2. **Check operator logs:**
   ```bash
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --tail=20
   ```

3. **Test reconciliation:**
   ```bash
   # Create test resource
   kubectl apply -f - <<EOF
   apiVersion: k8sio.auth/v1
   kind: User
   metadata:
     name: test-recovery
   spec:
     roleRef: viewer
     namespaces:
       - default
   EOF

   # Verify it's processed
   kubectl get users.k8sio.auth test-recovery -o yaml

   # Cleanup
   kubectl delete users.k8sio.auth test-recovery
   ```

4. **Verify metrics are being collected:**
   ```bash
   curl http://localhost:8081/actuator/metrics | head
   ```

## Escalation

If the above steps don't resolve the issue:

1. **Page on-call engineer** if outside business hours
2. **Create incident ticket** with:
   - Timestamp of alert
   - Steps already taken
   - Current pod status
   - Recent logs

## Prevention

- Enable Pod Disruption Budget
- Use multiple replicas
- Set up proper resource requests/limits
- Monitor error budget consumption
- Regular capacity reviews

## Related Runbooks

- [High Error Rate](./high-error-rate.md)
- [Reconciliation Stuck](./reconciliation-stuck.md)
