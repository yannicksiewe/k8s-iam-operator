# Integrating with External Secrets Operator

This guide explains how to use k8s-iam-operator alongside [External Secrets Operator (ESO)](https://external-secrets.io/) for complete identity and secrets management.

## Overview

**k8s-iam-operator** manages:
- User identities (human users + service accounts)
- Groups and RBAC bindings
- Kubeconfig generation for cluster access
- Namespace isolation with quotas and network policies

**External Secrets Operator** manages:
- Syncing secrets from external providers (AWS SM, Vault, etc.)
- Secret rotation
- Cross-namespace secret sharing

Together, they provide a complete identity and secrets management solution.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Kubernetes Cluster                              │
│                                                                             │
│  ┌─────────────────────┐       ┌─────────────────────────────────────────┐ │
│  │  k8s-iam-operator   │       │       External Secrets Operator         │ │
│  │                     │       │                                         │ │
│  │  - User CRDs        │       │  - ExternalSecret CRDs                  │ │
│  │  - Group CRDs       │       │  - SecretStore CRDs                     │ │
│  │  - ServiceAccounts  │       │  - ClusterSecretStore CRDs              │ │
│  │  - RBAC Bindings    │       │                                         │ │
│  │  - Kubeconfigs      │       │                                         │ │
│  └─────────────────────┘       └─────────────────────────────────────────┘ │
│            │                                    │                          │
│            ▼                                    ▼                          │
│  ┌─────────────────────┐       ┌─────────────────────────────────────────┐ │
│  │   User Namespace    │       │           External Providers            │ │
│  │   (alice)           │       │                                         │ │
│  │                     │       │  - AWS Secrets Manager                  │ │
│  │   - kubeconfig      │◄──────│  - HashiCorp Vault                      │ │
│  │   - aws-credentials │       │  - GCP Secret Manager                   │ │
│  │   - app-secrets     │       │  - Azure Key Vault                      │ │
│  └─────────────────────┘       └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Installation

### 1. Install k8s-iam-operator

```bash
helm install k8s-iam-operator ./charts/k8s-iam-operator \
  --namespace iam \
  --create-namespace
```

### 2. Install External Secrets Operator

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace
```

## Use Cases

### Use Case 1: Human User with AWS Access

Create a human user who needs access to AWS credentials for their work.

#### Step 1: Create the User

```yaml
# user-alice.yaml
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: alice
  namespace: iam
spec:
  type: human
  namespaceConfig:
    labels:
      team: data-engineering
    quota:
      cpu: "4"
      memory: "8Gi"
  CRoles:
    - namespace: data-pipelines
      clusterRole: edit
```

```bash
kubectl apply -f user-alice.yaml
```

This creates:
- ServiceAccount `alice` in `iam` namespace
- Namespace `alice` with quota
- Kubeconfig secret in `alice` namespace

#### Step 2: Create ClusterSecretStore (Admin)

```yaml
# cluster-secret-store.yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: eu-west-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
```

```bash
kubectl apply -f cluster-secret-store.yaml
```

#### Step 3: Create ExternalSecret in User's Namespace

```yaml
# alice-aws-credentials.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: aws-credentials
  namespace: alice  # User's namespace
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: aws-credentials
    creationPolicy: Owner
  data:
    - secretKey: AWS_ACCESS_KEY_ID
      remoteRef:
        key: data-team/aws-readonly
        property: access_key
    - secretKey: AWS_SECRET_ACCESS_KEY
      remoteRef:
        key: data-team/aws-readonly
        property: secret_key
```

```bash
kubectl apply -f alice-aws-credentials.yaml
```

Now Alice has:
- Her own namespace with kubeconfig
- AWS credentials synced from Secrets Manager
- RBAC access to data-pipelines namespace

### Use Case 2: Application ServiceAccount with Database Credentials

Create a service account for an application that needs database credentials.

#### Step 1: Create the ServiceAccount User

```yaml
# app-backend.yaml
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: backend-api
  namespace: iam
spec:
  type: serviceAccount
  targetNamespace: production
  CRoles:
    - namespace: production
      clusterRole: view
```

```bash
kubectl apply -f app-backend.yaml
```

#### Step 2: Create ExternalSecret for Database Credentials

```yaml
# backend-db-credentials.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: production
spec:
  refreshInterval: 30m
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: database-credentials
  data:
    - secretKey: DB_HOST
      remoteRef:
        key: production/database
        property: host
    - secretKey: DB_USER
      remoteRef:
        key: production/database
        property: username
    - secretKey: DB_PASSWORD
      remoteRef:
        key: production/database
        property: password
```

#### Step 3: Deploy Application Using Both

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-api
  namespace: production
spec:
  template:
    spec:
      serviceAccountName: backend-api  # Created by k8s-iam-operator
      containers:
        - name: api
          image: myapp/backend:latest
          envFrom:
            - secretRef:
                name: database-credentials  # Synced by ESO
```

### Use Case 3: Shared Credentials Across Teams

Share credentials across multiple user namespaces using ESO's ClusterExternalSecret.

#### Step 1: Create ClusterExternalSecret

```yaml
# shared-github-token.yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterExternalSecret
metadata:
  name: shared-github-token
spec:
  # Target namespaces with specific label
  namespaceSelector:
    matchLabels:
      team: platform
  externalSecretSpec:
    refreshInterval: 1h
    secretStoreRef:
      name: vault
      kind: ClusterSecretStore
    target:
      name: github-token
    data:
      - secretKey: GITHUB_TOKEN
        remoteRef:
          key: secret/data/ci/github
          property: token
```

#### Step 2: Create Users with Team Label

```yaml
# platform-users.yaml
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: platform-engineer-1
  namespace: iam
spec:
  type: human
  namespaceConfig:
    labels:
      team: platform  # Matches ClusterExternalSecret selector
---
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: platform-engineer-2
  namespace: iam
spec:
  type: human
  namespaceConfig:
    labels:
      team: platform
```

Now all platform team members automatically get the GitHub token in their namespaces.

## RBAC for External Secrets

Grant users permission to create ExternalSecrets in their namespaces.

### Create ClusterRole

```yaml
# external-secrets-user-role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: external-secrets-user
rules:
  - apiGroups: ["external-secrets.io"]
    resources: ["externalsecrets"]
    verbs: ["get", "list", "watch", "create", "update", "delete"]
  - apiGroups: ["external-secrets.io"]
    resources: ["secretstores"]
    verbs: ["get", "list", "watch"]
```

### Grant to User via k8s-iam-operator

```yaml
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: developer
  namespace: iam
spec:
  type: human
  CRoles:
    - namespace: developer  # Their own namespace
      clusterRole: external-secrets-user
```

## Best Practices

### 1. Use Namespace Labels for Targeting

Label user namespaces consistently for ClusterExternalSecret targeting:

```yaml
spec:
  namespaceConfig:
    labels:
      team: backend
      environment: development
      cost-center: engineering
```

### 2. Limit Secret Scope

Use namespace-scoped SecretStores when possible:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: team-vault
  namespace: alice
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret/data/teams/alice"  # Scoped path
```

### 3. Set Appropriate Refresh Intervals

Balance freshness with API rate limits:

```yaml
spec:
  refreshInterval: 1h    # Most secrets
  # refreshInterval: 5m  # Frequently rotated credentials
```

### 4. Use Immutable Secrets for Sensitive Data

```yaml
spec:
  target:
    immutable: true  # Prevents modifications
```

## Monitoring

### Combined Metrics

Monitor both operators:

```yaml
# Prometheus rules
groups:
  - name: iam-secrets
    rules:
      # k8s-iam-operator metrics
      - alert: UserCreationFailed
        expr: increase(k8s_iam_operator_handler_errors_total{handler="user"}[5m]) > 0

      # External Secrets metrics
      - alert: SecretSyncFailed
        expr: increase(externalsecret_sync_calls_error_total[5m]) > 0

      # Combined: User without synced secrets
      - alert: UserMissingSecrets
        expr: |
          kube_namespace_labels{label_k8sio_auth_type="human"}
          unless
          kube_secret_info{secret=~".*-credentials"}
```

## Troubleshooting

### Secret Not Syncing

1. Check ESO logs:
   ```bash
   kubectl logs -n external-secrets -l app.kubernetes.io/name=external-secrets
   ```

2. Check ExternalSecret status:
   ```bash
   kubectl get externalsecret -n <namespace> -o yaml
   ```

### User Can't Create ExternalSecrets

1. Verify RBAC:
   ```bash
   kubectl auth can-i create externalsecrets -n <namespace> --as=system:serviceaccount:iam:<user>
   ```

2. Check User CRD for correct roles:
   ```bash
   kubectl get user <name> -n iam -o yaml
   ```

## See Also

- [External Secrets Operator Documentation](https://external-secrets.io/)
- [k8s-iam-operator User Guide](../README.md)
- [Production Guide](../production-guide.md)
