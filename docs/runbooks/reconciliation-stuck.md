# Runbook: Reconciliation Stuck

**Alert Name:** `IAMOperatorReconciliationStuck`
**Severity:** Warning
**Service:** k8s-iam-operator

## Overview

This runbook addresses the situation where the k8s-iam-operator appears to have stopped processing resources.

## Impact

- New and updated resources are not being reconciled
- Users may not receive expected access changes
- System state may diverge from desired state

**User Impact:** All pending changes are blocked.

## Alert Definition

```yaml
alert: IAMOperatorReconciliationStuck
expr: increase(kopf_handler_duration_seconds_count[10m]) == 0
for: 15m
```

## Possible Causes

1. **Operator is not running** - Pods crashed or not scheduled
2. **No resources to process** - Normal if no changes occur
3. **Handler deadlock** - Code issue causing handler to hang
4. **Kubernetes API unavailable** - Cannot watch for changes
5. **Watch disconnected** - Lost connection to API server
6. **Resource exhaustion** - Out of memory or file descriptors

## Diagnosis Steps

### 1. Check if Operator is Running

```bash
kubectl get pods -n iam -l app.kubernetes.io/name=k8s-iam-operator
kubectl get deployment -n iam k8s-iam-operator
```

If pods are not running, see [Operator Down runbook](./operator-down.md).

### 2. Check if There Are Resources to Process

```bash
# Check if there are any resources
kubectl get users.k8sio.auth -A --no-headers | wc -l
kubectl get groups.k8sio.auth -A --no-headers | wc -l
kubectl get roles.k8sio.auth -A --no-headers | wc -l
```

If there are no resources and no expected changes, this may be a false positive.

### 3. Check Operator Logs

```bash
# Recent logs
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --tail=100

# Look for watch errors
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -i "watch\|connection\|disconnect"

# Look for exceptions
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -i "exception\|traceback"
```

### 4. Check Operator Health

```bash
# Port forward to operator
kubectl port-forward -n iam svc/k8s-iam-operator 8081:8081 &

# Check health endpoint
curl http://localhost:8081/actuator/health

# Check if metrics are being updated
curl http://localhost:8081/actuator/metrics | grep kopf
```

### 5. Check Resource State

```bash
# Check if any resources are stuck
kubectl get users.k8sio.auth -A -o jsonpath='{range .items[*]}{.metadata.name}: {.status.phase}{"\n"}{end}'
```

### 6. Check API Server Connectivity

```bash
# From operator pod
kubectl exec -n iam -it $(kubectl get pods -n iam -l app.kubernetes.io/name=k8s-iam-operator -o jsonpath='{.items[0].metadata.name}') -- wget -qO- https://kubernetes.default.svc/healthz --no-check-certificate
```

### 7. Check System Resources

```bash
# Check operator resource usage
kubectl top pods -n iam

# Check if pod is OOMKilled
kubectl describe pod -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -A5 "Last State"
```

## Resolution Steps

### Scenario 1: Watch Disconnected

**Symptom:** Logs show connection errors or no recent watch events

**Resolution:**
1. Restart the operator:
   ```bash
   kubectl rollout restart deployment -n iam k8s-iam-operator
   ```

2. Verify watches are re-established:
   ```bash
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --since=1m | grep -i "watch\|handler"
   ```

### Scenario 2: Handler Stuck/Deadlock

**Symptom:** One or more handlers show long duration, no completion

**Resolution:**
1. Get thread dump (if supported):
   ```bash
   kubectl exec -n iam -it <pod-name> -- kill -3 1
   kubectl logs -n iam <pod-name> | tail -100
   ```

2. Force restart:
   ```bash
   kubectl delete pod -n iam -l app.kubernetes.io/name=k8s-iam-operator --force --grace-period=0
   ```

### Scenario 3: API Server Issues

**Symptom:** Cannot connect to API server

**Resolution:**
1. Check API server health:
   ```bash
   kubectl get --raw /healthz
   ```

2. If API server is down, this is a cluster-level issue - escalate

3. If network policy is blocking:
   ```bash
   kubectl get networkpolicy -n iam -o yaml
   ```

### Scenario 4: Resource Exhaustion

**Symptom:** OOMKilled or high resource usage

**Resolution:**
1. Increase resource limits:
   ```yaml
   resources:
     limits:
       memory: 1Gi
       cpu: 1000m
   ```

2. Apply updated configuration:
   ```bash
   helm upgrade k8s-iam-operator ./charts/k8s-iam-operator -n iam --reuse-values --set resources.limits.memory=1Gi
   ```

### Scenario 5: False Positive (No Work to Do)

**Symptom:** No resources exist or no changes expected

**Resolution:**
1. Create a test resource to verify reconciliation works:
   ```bash
   kubectl apply -f - <<EOF
   apiVersion: k8sio.auth/v1
   kind: User
   metadata:
     name: reconciliation-test
   spec:
     roleRef: viewer
     namespaces:
       - default
   EOF
   ```

2. Check if it was processed:
   ```bash
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --since=1m | grep reconciliation-test
   ```

3. Clean up:
   ```bash
   kubectl delete users.k8sio.auth reconciliation-test
   ```

4. If test succeeds, adjust alert threshold or add resource existence check to alert

## Recovery Verification

1. **Verify reconciliation is working:**
   ```bash
   # Check for recent handler activity
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --since=5m | grep -i "handler\|reconcil"
   ```

2. **Verify metrics are updating:**
   ```bash
   # Check metrics endpoint
   kubectl port-forward -n iam svc/k8s-iam-operator 8081:8081 &

   # Get handler count, wait 1 minute, get again - should increase
   curl -s http://localhost:8081/actuator/metrics | grep handler_duration_seconds_count
   ```

3. **Test end-to-end:**
   ```bash
   # Create test resource
   kubectl apply -f - <<EOF
   apiVersion: k8sio.auth/v1
   kind: User
   metadata:
     name: recovery-test-$(date +%s)
   spec:
     roleRef: viewer
     namespaces:
       - default
   EOF

   # Verify ServiceAccount was created
   kubectl get sa -n iam | grep recovery-test
   ```

## Escalation

If reconciliation remains stuck after restart:

1. **Collect diagnostics:**
   ```bash
   # Full operator logs
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --timestamps > operator-full.log

   # Describe all operator pods
   kubectl describe pods -n iam -l app.kubernetes.io/name=k8s-iam-operator > pods-describe.txt

   # Events
   kubectl get events -n iam --sort-by='.lastTimestamp' > events.txt
   ```

2. **Page senior engineer** with:
   - Duration of stuck state
   - Attempted resolutions
   - Diagnostic files

## Prevention

- Set up proactive monitoring for reconciliation rate
- Configure appropriate resource limits
- Enable tracing for debugging
- Regular chaos testing (kill pods randomly)

## Related Runbooks

- [Operator Down](./operator-down.md)
- [High Error Rate](./high-error-rate.md)
