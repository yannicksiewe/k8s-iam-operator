# Troubleshooting Guide

This guide covers common issues and their solutions when operating k8s-iam-operator.

## Table of Contents

- [User Not Getting Access](#user-not-getting-access)
- [Kubeconfig Not Generated](#kubeconfig-not-generated)
- [Operator Not Starting](#operator-not-starting)
- [RBAC Binding Errors](#rbac-binding-errors)
- [Resource Not Being Processed](#resource-not-being-processed)
- [Performance Issues](#performance-issues)
- [Tracing Issues](#tracing-issues)

## User Not Getting Access

### Symptoms
- User cannot access cluster resources
- Authentication failures
- Permission denied errors

### Diagnosis

1. **Check User resource status:**
   ```bash
   kubectl get users.k8sio.auth <username> -o yaml
   ```

2. **Verify ServiceAccount exists:**
   ```bash
   kubectl get sa -n iam <username>
   ```

3. **Check RoleBindings:**
   ```bash
   kubectl get rolebindings -A | grep <username>
   kubectl get clusterrolebindings | grep <username>
   ```

4. **Test permissions:**
   ```bash
   kubectl auth can-i --list --as=system:serviceaccount:iam:<username>
   ```

### Solutions

**Missing RoleBinding:**
```bash
# Check operator logs for binding errors
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -i binding
```

**Incorrect namespace:**
Ensure the User resource specifies the correct target namespaces in the spec.

**Role doesn't exist:**
```bash
kubectl get roles -A | grep <role-name>
kubectl get clusterroles | grep <role-name>
```

## Kubeconfig Not Generated

### Symptoms
- Kubeconfig secret not created
- Secret exists but is empty
- Token not populated in kubeconfig

### Diagnosis

1. **Check if secret exists:**
   ```bash
   kubectl get secrets -n iam | grep kubeconfig
   ```

2. **Verify secret contents:**
   ```bash
   kubectl get secret <user>-kubeconfig -n iam -o jsonpath='{.data.kubeconfig}' | base64 -d
   ```

3. **Check ServiceAccount token:**
   ```bash
   kubectl get secret <user>-token -n iam -o yaml
   ```

### Solutions

**Token not auto-created (K8s 1.24+):**

In Kubernetes 1.24+, ServiceAccount tokens are not auto-created. The operator should create them explicitly:

```bash
# Verify the operator created a token secret
kubectl get secrets -n iam -l kubernetes.io/service-account.name=<username>
```

**Cluster API endpoint wrong:**

Check the operator configuration for the correct cluster API endpoint:
```bash
kubectl get configmap -n iam k8s-iam-operator-config -o yaml
```

## Operator Not Starting

### Symptoms
- Pod in CrashLoopBackOff
- Pod stuck in Pending
- Pod not scheduled

### Diagnosis

1. **Check pod status:**
   ```bash
   kubectl get pods -n iam
   kubectl describe pod -n iam -l app.kubernetes.io/name=k8s-iam-operator
   ```

2. **Check logs:**
   ```bash
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator --previous
   ```

3. **Check events:**
   ```bash
   kubectl get events -n iam --sort-by='.lastTimestamp'
   ```

### Solutions

**Insufficient resources:**
```yaml
# Increase resource limits in values.yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 200m
    memory: 256Mi
```

**Missing CRDs:**
```bash
kubectl apply -f crd/
```

**RBAC issues:**
```bash
# Check if ClusterRole exists
kubectl get clusterrole k8s-iam-operator

# Check ClusterRoleBinding
kubectl get clusterrolebinding k8s-iam-operator
```

**Image pull issues:**
```bash
kubectl describe pod -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -A5 Events
```

## RBAC Binding Errors

### Symptoms
- Errors in operator logs about binding creation
- 403 Forbidden errors
- "cannot bind" errors

### Diagnosis

1. **Check operator logs:**
   ```bash
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -i rbac
   ```

2. **Verify operator permissions:**
   ```bash
   kubectl auth can-i create rolebindings --as=system:serviceaccount:iam:k8s-iam-operator -n default
   ```

### Solutions

**Operator lacks permissions:**

Ensure the operator's ClusterRole has sufficient permissions:
```yaml
rules:
- apiGroups: ["rbac.authorization.k8s.io"]
  resources: ["rolebindings", "clusterrolebindings"]
  verbs: ["create", "delete", "get", "list", "patch", "update", "watch"]
```

**Escalation prevention:**

The operator cannot grant permissions it doesn't have. Ensure the operator's ServiceAccount has all roles it needs to assign.

## Resource Not Being Processed

### Symptoms
- CR created but nothing happens
- Status not updated
- No operator activity

### Diagnosis

1. **Check resource status:**
   ```bash
   kubectl get users.k8sio.auth -A
   kubectl describe users.k8sio.auth <name>
   ```

2. **Check operator is watching:**
   ```bash
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator | tail -50
   ```

3. **Verify CRD version:**
   ```bash
   kubectl get crd users.k8sio.auth -o jsonpath='{.spec.versions[*].name}'
   ```

### Solutions

**API version mismatch:**

Ensure your CR uses the correct API version:
```yaml
apiVersion: k8sio.auth/v1  # Must match CRD
kind: User
```

**Operator not running:**
```bash
kubectl get pods -n iam
kubectl rollout restart deployment -n iam k8s-iam-operator
```

**Handler error:**

Check for exceptions in the logs:
```bash
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator | grep -i error
```

## Performance Issues

### Symptoms
- Slow reconciliation
- High memory usage
- CPU throttling

### Diagnosis

1. **Check resource usage:**
   ```bash
   kubectl top pods -n iam
   ```

2. **Check reconciliation metrics:**
   ```bash
   curl http://<operator-pod-ip>:8081/actuator/metrics | grep reconcil
   ```

3. **Count managed resources:**
   ```bash
   kubectl get users.k8sio.auth -A --no-headers | wc -l
   kubectl get groups.k8sio.auth -A --no-headers | wc -l
   ```

### Solutions

**Increase resources:**
```yaml
resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 512Mi
```

**Enable HPA:**
```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
```

**Optimize batch size:**

If managing many resources, consider grouping related changes.

## Tracing Issues

### Symptoms
- Traces not appearing in Jaeger/Tempo
- Missing spans
- Connection errors

### Diagnosis

1. **Check tracing config:**
   ```bash
   kubectl get deployment -n iam k8s-iam-operator -o yaml | grep -A5 ENABLE_TRACING
   ```

2. **Verify endpoint connectivity:**
   ```bash
   kubectl exec -n iam -it <operator-pod> -- wget -qO- http://tempo.monitoring:4317/
   ```

### Solutions

**Enable tracing:**
```yaml
tracing:
  enabled: true
  endpoint: "http://tempo.monitoring:4317/"
```

**Network policy blocking:**

Ensure network policy allows egress to the tracing endpoint.

## Getting Help

If these solutions don't resolve your issue:

1. **Collect diagnostics:**
   ```bash
   kubectl get pods -n iam -o yaml > pods.yaml
   kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator > operator.log
   kubectl get events -n iam > events.txt
   ```

2. **Open an issue** with the collected information at:
   https://github.com/yannick-siewe/k8s-iam-operator/issues
