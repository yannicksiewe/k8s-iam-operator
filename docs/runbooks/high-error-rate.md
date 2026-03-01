# Runbook: High Error Rate

**Alert Name:** `IAMOperatorReconciliationErrors`
**Severity:** Warning
**Service:** k8s-iam-operator

## Overview

This runbook addresses high reconciliation error rates in the k8s-iam-operator.

## Impact

- Some User/Group/Role resources may not be processed correctly
- RBAC bindings may be incomplete
- Users may not have expected access
- Kubeconfig generation may fail for some users

**User Impact:** Partial degradation - some users affected.

## Alert Definition

```yaml
alert: IAMOperatorReconciliationErrors
expr: increase(kopf_handler_errors_total[5m]) > 5
for: 5m
```

## Diagnosis Steps

### 1. Check Error Rate and Trend

```bash
# Check recent error count
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --since=10m | grep -i error | wc -l

# View actual errors
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --since=10m | grep -i error
```

### 2. Identify Affected Resources

```bash
# Check which resources have issues
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --since=10m | grep -i "failed\|error" | grep -oP "name=['\"]?\K[^'\" ]+"
```

### 3. Check Resource Status

```bash
# List all users with their status
kubectl get users.k8sio.auth -A

# Check specific problematic resource
kubectl describe users.k8sio.auth <name>
```

### 4. Check Kubernetes API Health

```bash
# Verify API server is responsive
kubectl cluster-info

# Check API server metrics (if available)
kubectl get --raw /healthz
```

### 5. Check RBAC Permissions

```bash
# Verify operator has necessary permissions
kubectl auth can-i --list --as=system:serviceaccount:iam:k8s-iam-operator
```

## Common Error Patterns

### Pattern 1: RBAC Permission Errors

**Symptom:** Errors containing "forbidden" or "cannot create/update"

```bash
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -i forbidden
```

**Resolution:**
1. Check ClusterRole:
   ```bash
   kubectl get clusterrole k8s-iam-operator -o yaml
   ```

2. Ensure role has required permissions:
   ```yaml
   rules:
   - apiGroups: ["rbac.authorization.k8s.io"]
     resources: ["rolebindings", "clusterrolebindings", "roles", "clusterroles"]
     verbs: ["*"]
   ```

3. Reapply RBAC:
   ```bash
   kubectl apply -f crd/rbac.yaml
   ```

### Pattern 2: Resource Validation Errors

**Symptom:** Errors about invalid spec or missing fields

```bash
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -i "validation\|invalid\|required"
```

**Resolution:**
1. Identify problematic resources:
   ```bash
   kubectl get users.k8sio.auth -A -o yaml | grep -B20 "status:"
   ```

2. Fix resource specification or delete invalid resources

### Pattern 3: Namespace Not Found

**Symptom:** Errors about namespace not existing

```bash
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -i "namespace.*not found"
```

**Resolution:**
1. Create missing namespace:
   ```bash
   kubectl create namespace <missing-namespace>
   ```

2. Or update User spec to remove non-existent namespace

### Pattern 4: Referenced Role Not Found

**Symptom:** Errors about role or clusterrole not found

```bash
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -i "role.*not found"
```

**Resolution:**
1. Check if role exists:
   ```bash
   kubectl get clusterroles | grep <role-name>
   ```

2. Create missing role or update User spec

### Pattern 5: API Rate Limiting

**Symptom:** 429 errors or "too many requests"

```bash
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -i "429\|rate limit\|too many"
```

**Resolution:**
1. This is usually transient - errors should auto-resolve
2. If persistent, check if there's a spike in resource changes
3. Consider scaling the operator

### Pattern 6: Network/Connectivity Issues

**Symptom:** Timeout errors or connection refused

```bash
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -i "timeout\|connection refused\|network"
```

**Resolution:**
1. Check network policy:
   ```bash
   kubectl get networkpolicy -n iam
   ```

2. Verify egress is allowed to API server
3. Check if CNI is healthy

## Resolution Steps

### 1. For Transient Errors

If errors are < 10/minute and decreasing:
- Monitor for 10-15 minutes
- Errors should auto-resolve through retries

### 2. For Persistent Errors

1. **Identify pattern** from logs
2. **Apply appropriate fix** based on pattern above
3. **Restart operator** if needed:
   ```bash
   kubectl rollout restart deployment -n iam k8s-iam-operator
   ```

### 3. For Bulk Resource Issues

If many resources are affected:

1. **Pause processing** (scale to 0):
   ```bash
   kubectl scale deployment -n iam k8s-iam-operator --replicas=0
   ```

2. **Fix underlying issue**

3. **Resume processing**:
   ```bash
   kubectl scale deployment -n iam k8s-iam-operator --replicas=2
   ```

## Recovery Verification

1. **Check error rate decreasing:**
   ```bash
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --since=5m | grep -i error | wc -l
   ```

2. **Verify resources are being processed:**
   ```bash
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --since=5m | grep -i "reconciled\|created\|updated"
   ```

3. **Check previously failing resources:**
   ```bash
   kubectl describe users.k8sio.auth <previously-failing-resource>
   ```

## Escalation

If error rate remains elevated after 30 minutes:

1. **Collect diagnostics:**
   ```bash
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --since=1h > operator-logs.txt
   kubectl get events -n iam > events.txt
   ```

2. **Page senior engineer** with:
   - Error rate metrics
   - Sample error messages
   - Actions already taken

## Prevention

- Validate resources before applying (use admission webhooks)
- Monitor error budget
- Set up alerting on error rate trends
- Regular RBAC audits

## Related Runbooks

- [Operator Down](./operator-down.md)
- [Reconciliation Stuck](./reconciliation-stuck.md)
