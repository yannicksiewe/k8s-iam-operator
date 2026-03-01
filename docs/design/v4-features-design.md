# k8s-iam-operator v4.0 Feature Design

## Executive Summary

This document outlines the design for three major new features to transform k8s-iam-operator into a comprehensive identity and credential management platform for Kubernetes:

1. **Pod-Based ServiceAccount Management** - Automatic SA creation via pod annotations
2. **Credential Sharing (External Secrets)** - Share AWS, GitHub, DockerHub credentials with pods
3. **Audit Dashboard** - Visual monitoring of all IAM operations

---

## Current State vs Target State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CURRENT STATE (v3.x)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  User CRD ────► ServiceAccount + Namespace + Kubeconfig (Human Users)      │
│  User CRD ────► ServiceAccount in specified namespace (App/SA Users)       │
│  Group CRD ───► RBAC RoleBindings for groups                               │
│  Role CRD ────► Custom Roles/ClusterRoles                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                                    ↓

┌─────────────────────────────────────────────────────────────────────────────┐
│                           TARGET STATE (v4.0)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  EXISTING:                                                                  │
│  ├── User CRD (Human) ──► Namespace + Kubeconfig                           │
│  ├── User CRD (SA) ─────► ServiceAccount in app namespace                  │
│  ├── Group CRD ─────────► RBAC bindings                                    │
│  └── Role CRD ──────────► Custom roles                                     │
│                                                                             │
│  NEW FEATURES:                                                              │
│  ├── Pod Annotations ───► Auto-create SA for specific pod                  │
│  ├── CredentialShare CRD ► Shared secrets (AWS, GitHub, DockerHub)         │
│  ├── Pod Annotations ───► Inject shared credentials into pods              │
│  └── Audit Dashboard ───► Grafana dashboard for IAM operations             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Feature 1: Pod-Based ServiceAccount Management

### Overview

Allow pods to request dedicated ServiceAccounts via annotations. The operator watches pods and automatically creates/manages SAs bound specifically to those pods.

### Annotations

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  namespace: production
  annotations:
    # Request a dedicated SA for this pod
    iam.k8sio.auth/sa-request: "true"

    # Optional: Specify roles for the SA
    iam.k8sio.auth/cluster-roles: "view,secrets-reader"
    iam.k8sio.auth/roles: "app-config-reader"

    # Optional: Custom SA name (default: {pod-name}-sa)
    iam.k8sio.auth/sa-name: "my-custom-sa"
spec:
  # SA will be automatically set by operator
  # serviceAccountName: my-app-sa  <-- injected by operator
  containers:
    - name: app
      image: myapp:latest
```

### Behavior

| Event | Operator Action |
|-------|-----------------|
| Pod created with `sa-request: "true"` | Create SA, bind roles, mutate pod to use SA |
| Annotation `cluster-roles` changed | Update SA's role bindings |
| Annotation removed | Delete SA and bindings |
| Pod deleted | Delete SA and bindings (ownership) |

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     Pod Annotation Watcher                      │
│                                                                │
│   Pod Created ──► Validate ──► Create SA ──► Bind Roles ──►   │
│                                    │                           │
│                                    ▼                           │
│                           Mutate Pod spec                      │
│                           (set serviceAccountName)             │
│                                    │                           │
│                                    ▼                           │
│   Pod Updated ◄── Watch for ◄── SA with OwnerReference        │
│                   annotation       to Pod                      │
│                   changes                                      │
└────────────────────────────────────────────────────────────────┘
```

### Implementation Components

1. **New Kopf Handler**: `pod_handlers.py`
   - Watch pods with `iam.k8sio.auth/*` annotations
   - Use `kopf.on.create`, `kopf.on.update`, `kopf.on.delete`

2. **New Service**: `pod_sa_service.py`
   - `create_pod_sa()`: Create SA with OwnerReference to pod
   - `update_pod_sa()`: Update role bindings
   - `delete_pod_sa()`: Cleanup (automatic via OwnerReference)

3. **Mutating Webhook** (Optional, for pod mutation):
   - Inject `serviceAccountName` before pod creation
   - Or use init-time annotation processing

---

## Feature 2: Credential Sharing (External Secrets)

### Overview

Allow pods to request access to shared credentials (AWS, GitHub, DockerHub, etc.) via annotations. Credentials can be stored in:
- Kubernetes Secrets (managed by operator)
- AWS Secrets Manager
- HashiCorp Vault (future)

### New CRD: CredentialShare

```yaml
apiVersion: k8sio.auth/v1
kind: CredentialShare
metadata:
  name: aws-s3-readonly
  namespace: iam
spec:
  # Credential type
  type: aws  # aws | github | dockerhub | generic

  # Source of the credential
  source:
    # Option 1: From Kubernetes Secret
    secretRef:
      name: aws-credentials
      namespace: iam

    # Option 2: From AWS Secrets Manager
    awsSecretsManager:
      secretId: "prod/aws/s3-readonly"
      region: "eu-west-1"
      # Optional: Use IRSA or specify credentials
      roleArn: "arn:aws:iam::123456789:role/secrets-reader"

    # Option 3: From Vault (future)
    vault:
      path: "secret/data/aws/s3"
      role: "k8s-iam-operator"

  # What to share
  data:
    - key: AWS_ACCESS_KEY_ID
      path: "access_key"  # Path in source
    - key: AWS_SECRET_ACCESS_KEY
      path: "secret_key"
    - key: AWS_REGION
      value: "eu-west-1"  # Static value

  # Access control
  allowedNamespaces:
    - production
    - staging

  # Optional: Allowed pod selectors
  allowedPodLabels:
    app.kubernetes.io/component: backend

  # Refresh interval for external sources
  refreshInterval: 1h
status:
  lastSynced: "2024-01-15T10:30:00Z"
  conditions:
    - type: Ready
      status: "True"
```

### Pod Annotation for Credential Access

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader
  namespace: production
  annotations:
    # Request credentials
    iam.k8sio.auth/credentials: "aws-s3-readonly,github-readonly"

    # How to inject (env or volume)
    iam.k8sio.auth/credential-injection: "env"  # env | volume | both
spec:
  containers:
    - name: app
      image: myapp:latest
      # Operator injects:
      # env:
      #   - name: AWS_ACCESS_KEY_ID
      #     valueFrom:
      #       secretKeyRef: ...
```

### Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     Credential Sharing Architecture                       │
│                                                                          │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐    │
│  │ AWS Secrets Mgr │     │ Kubernetes      │     │ HashiCorp Vault │    │
│  │                 │     │ Secrets         │     │ (future)        │    │
│  └────────┬────────┘     └────────┬────────┘     └────────┬────────┘    │
│           │                       │                       │              │
│           └───────────────────────┼───────────────────────┘              │
│                                   │                                      │
│                                   ▼                                      │
│                    ┌──────────────────────────┐                          │
│                    │   CredentialShare CRD    │                          │
│                    │   Operator Handler       │                          │
│                    └──────────────────────────┘                          │
│                                   │                                      │
│                                   ▼                                      │
│                    ┌──────────────────────────┐                          │
│                    │  Local Synced Secrets    │                          │
│                    │  (in target namespaces)  │                          │
│                    └──────────────────────────┘                          │
│                                   │                                      │
│                                   ▼                                      │
│    ┌─────────────────────────────────────────────────────────────┐      │
│    │                    Pod Watcher                               │      │
│    │  Pod with annotation ──► Validate access ──► Inject secret   │      │
│    └─────────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────────┘
```

### Implementation Components

1. **New CRD**: `credentialshare_crd.yaml`
2. **New Handler**: `credential_handlers.py`
3. **New Services**:
   - `credential_share_service.py`: Manage CredentialShare lifecycle
   - `credential_sync_service.py`: Sync from external sources
   - `credential_injector_service.py`: Inject into pods
4. **New Repository**: `external_secrets_repository.py`
   - AWS Secrets Manager client
   - Vault client (future)

---

## Feature 3: Audit Logging & Dashboard

### Overview

Comprehensive audit logging of all IAM operations with a Grafana dashboard for visualization.

### Audit Events

| Event Type | Description |
|------------|-------------|
| `user.created` | User CRD created |
| `user.updated` | User CRD updated |
| `user.deleted` | User CRD deleted |
| `sa.created` | ServiceAccount created |
| `sa.bound_to_pod` | SA attached to pod |
| `credential.shared` | Credential shared with pod |
| `credential.accessed` | Pod accessed shared credential |
| `rbac.binding_created` | RoleBinding created |
| `rbac.binding_deleted` | RoleBinding deleted |

### Audit Log Format

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "event_type": "credential.shared",
  "actor": {
    "type": "operator",
    "name": "k8s-iam-operator"
  },
  "subject": {
    "type": "pod",
    "name": "my-app",
    "namespace": "production",
    "uid": "abc-123"
  },
  "resource": {
    "type": "CredentialShare",
    "name": "aws-s3-readonly",
    "namespace": "iam"
  },
  "action": "inject",
  "outcome": "success",
  "details": {
    "injection_type": "env",
    "keys_injected": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
  },
  "trace_id": "xyz-789"
}
```

### Metrics for Dashboard

```python
# Prometheus metrics
iam_users_total{type="human|sa", status="enabled|disabled"}
iam_groups_total{namespace="..."}
iam_credentials_shared_total{credential="...", namespace="..."}
iam_credential_access_total{credential="...", pod="...", namespace="..."}
iam_pod_sa_created_total{namespace="..."}
iam_rbac_bindings_total{type="role|clusterrole", namespace="..."}
iam_operations_total{operation="...", status="success|failure"}
iam_operation_duration_seconds{operation="..."}
```

### Grafana Dashboard Panels

1. **Overview**
   - Total users (human vs SA)
   - Total credentials shared
   - Operations per minute
   - Error rate

2. **User Management**
   - User creation timeline
   - Users by namespace
   - Kubeconfig generations

3. **Credential Sharing**
   - Credentials by type (AWS, GitHub, etc.)
   - Access patterns by pod/namespace
   - Credential sync status

4. **RBAC**
   - Bindings by role type
   - Permissions granted timeline
   - Most used roles

5. **Audit Trail**
   - Recent operations table
   - Failed operations
   - High-privilege operations

---

## Team Review

### Software Architect

#### Recommendations

1. **Modular Design**: Each feature should be a separate module
   ```
   app/
   ├── features/
   │   ├── pod_sa/           # Feature 1
   │   │   ├── handlers.py
   │   │   ├── service.py
   │   │   └── models.py
   │   ├── credentials/      # Feature 2
   │   │   ├── handlers.py
   │   │   ├── service.py
   │   │   ├── sources/
   │   │   │   ├── aws.py
   │   │   │   ├── vault.py
   │   │   │   └── k8s.py
   │   │   └── models.py
   │   └── audit/            # Feature 3
   │       ├── logger.py
   │       ├── metrics.py
   │       └── dashboard.py
   ```

2. **Event-Driven Architecture**: Use internal events for audit
   ```python
   class IAMEventBus:
       def emit(self, event: IAMEvent): ...
       def subscribe(self, handler: Callable): ...
   ```

3. **Feature Flags**: Allow enabling/disabling features
   ```yaml
   operator:
     features:
       podSA: true
       credentialSharing: true
       auditDashboard: true
   ```

### Security Architect

#### Threat Model

| Threat | Mitigation |
|--------|------------|
| Unauthorized credential access | Namespace + label restrictions in CredentialShare |
| SA privilege escalation | Validate requested roles against allowed list |
| Credential leakage in logs | Redact all credential values in audit logs |
| External secret exposure | Use IRSA/Workload Identity, short-lived tokens |

#### Recommendations

1. **Least Privilege**: Pod SA should only get requested roles
2. **Audit Everything**: Log all credential access
3. **Encryption**: Secrets at rest encryption required
4. **Network Policies**: Restrict operator's network access
5. **RBAC Validation**: Operator cannot grant more than it has

### DevOps Expert

#### CI/CD Additions

```yaml
# New test jobs
- integration-test-pod-sa
- integration-test-credentials
- security-scan-credentials

# New deployment configs
- AWS IRSA setup for Secrets Manager
- Vault integration (optional)
```

### SRE

#### SLOs for New Features

| Feature | SLO | Target |
|---------|-----|--------|
| Pod SA creation | P99 latency | < 5s |
| Credential sync | Freshness | < 5min |
| Audit logging | Availability | 99.9% |

#### Alerts

```yaml
- alert: CredentialSyncStale
  expr: time() - iam_credential_last_sync_timestamp > 600

- alert: PodSACreationSlow
  expr: histogram_quantile(0.99, iam_pod_sa_duration_seconds) > 5
```

### Product Owner

#### MVP Definition

**Phase 1 (v4.0)**: Pod SA Management
- Basic pod annotation support
- SA creation with role binding
- Audit logging

**Phase 2 (v4.1)**: Credential Sharing
- CredentialShare CRD
- Kubernetes secrets source
- AWS Secrets Manager integration

**Phase 3 (v4.2)**: Advanced Features
- Vault integration
- Grafana dashboard
- Credential rotation

#### User Stories

1. As a developer, I want my pod to automatically get a ServiceAccount so I don't have to create RBAC manually
2. As a platform admin, I want to share AWS credentials with approved pods without copying secrets
3. As a security officer, I want to audit all credential access in the cluster

---

## Implementation Roadmap

### Phase 1: Pod SA Management (v4.0) - 2 weeks

| Task | Priority | Effort |
|------|----------|--------|
| Pod watcher handler | P1 | 3d |
| Pod SA service | P1 | 2d |
| Role binding logic | P1 | 2d |
| Unit tests | P1 | 2d |
| Integration tests | P1 | 2d |
| Documentation | P1 | 1d |

### Phase 2: Credential Sharing (v4.1) - 3 weeks

| Task | Priority | Effort |
|------|----------|--------|
| CredentialShare CRD | P1 | 1d |
| Credential handlers | P1 | 3d |
| K8s secrets source | P1 | 2d |
| AWS SM integration | P1 | 3d |
| Pod credential injection | P1 | 3d |
| Access control logic | P1 | 2d |
| Tests | P1 | 3d |
| Documentation | P1 | 2d |

### Phase 3: Audit Dashboard (v4.2) - 1 week

| Task | Priority | Effort |
|------|----------|--------|
| Enhanced audit events | P2 | 2d |
| Prometheus metrics | P2 | 1d |
| Grafana dashboard | P2 | 2d |
| Documentation | P2 | 1d |

---

## File Changes Summary

### New Files

```
crd/
├── credentialshare_crd.yaml

app/
├── features/
│   ├── __init__.py
│   ├── pod_sa/
│   │   ├── __init__.py
│   │   ├── handlers.py
│   │   ├── service.py
│   │   └── models.py
│   ├── credentials/
│   │   ├── __init__.py
│   │   ├── handlers.py
│   │   ├── service.py
│   │   ├── injector.py
│   │   ├── sources/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── kubernetes.py
│   │   │   └── aws_secrets_manager.py
│   │   └── models.py
│   └── audit/
│       ├── __init__.py
│       ├── events.py
│       ├── metrics.py
│       └── bus.py

charts/k8s-iam-operator/
├── templates/
│   └── audit-dashboard.yaml (updated)
├── crds/
│   └── credentialshare.yaml
```

### Modified Files

```
app/
├── container.py          # Add new services
├── config.py             # Add feature flags
├── kopf_handlers/
│   └── __init__.py       # Register new handlers

charts/k8s-iam-operator/
├── values.yaml           # Feature flags, AWS config
├── templates/
│   ├── deployment.yaml   # AWS IRSA annotations
│   └── rbac.yaml         # New permissions
```

---

## Decision Points

1. **Pod Mutation**: Use Mutating Webhook or post-creation patching?
   - Recommendation: Post-creation patch (simpler, no webhook infra)

2. **External Secrets**: Build custom or use External Secrets Operator?
   - Recommendation: Build custom for tight integration, but make compatible

3. **Credential Refresh**: Pull-based or push-based?
   - Recommendation: Pull-based with configurable interval

4. **Audit Storage**: Logs only or also database?
   - Recommendation: Structured logs + Prometheus metrics (no database dependency)

---

## Next Steps

1. Review and approve this design
2. Create GitHub issues for each task
3. Start with Phase 1 (Pod SA Management)
4. Iterate based on feedback
