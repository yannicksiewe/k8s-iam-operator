# Audit & Compliance Guide

This guide covers audit logging for the k8s-iam-operator and how to achieve comprehensive audit visibility for user activities in your cluster.

## Table of Contents

- [Overview](#overview)
- [Operator Audit Logging (Built-in)](#operator-audit-logging-built-in)
- [Cluster Activity Audit (Kubernetes Native)](#cluster-activity-audit-kubernetes-native)
- [Grafana Audit Dashboard](#grafana-audit-dashboard)
- [Correlating Audit Logs](#correlating-audit-logs)
- [Log Aggregation](#log-aggregation)

## Overview

Audit logging in a Kubernetes IAM context has two distinct scopes:

| Scope | What It Tracks | Solution |
|-------|----------------|----------|
| **IAM Configuration** | User/Group/Role CRD changes, RBAC bindings, kubeconfig generation | Operator audit logging (built-in) |
| **Cluster Activity** | API calls made by users/SAs (create pods, get secrets, etc.) | Kubernetes API server audit logging |

The operator provides the first scope. For the second scope, you need to enable Kubernetes API server audit logging.

## Operator Audit Logging (Built-in)

### What It Tracks

The operator emits structured JSON audit logs for all IAM-related operations:

**User Operations:**
- User CRD creation/update/deletion
- ServiceAccount creation/deletion
- Kubeconfig secret generation/deletion

**Group Operations:**
- Group CRD creation/update/deletion
- Member changes

**RBAC Operations:**
- RoleBinding creation/deletion
- ClusterRoleBinding creation/deletion
- Role/ClusterRole assignment changes

**Namespace Operations:**
- Namespace creation for users
- Namespace deletion

### Enabling Operator Audit Logs

Audit logging is enabled by default. To disable it:

```yaml
# values.yaml
env:
  AUDIT_ENABLED: "false"
```

### Log Format

Audit events are emitted as structured JSON:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "category": "user",
  "action": "create",
  "outcome": "success",
  "actor": {
    "type": "operator",
    "name": "k8s-iam-operator"
  },
  "subject": {
    "type": "User",
    "name": "developer-alice",
    "namespace": "iam"
  },
  "message": "Created human user 'developer-alice'",
  "details": {
    "user_type": "human",
    "target_namespace": "team-alpha"
  },
  "trace_id": "abc123",
  "labels": {
    "user_type": "human"
  }
}
```

### Event Categories

| Category | Description |
|----------|-------------|
| `user` | User CRD and ServiceAccount operations |
| `group` | Group CRD operations |
| `role` | Role/ClusterRole CRD operations |
| `rbac` | RoleBinding/ClusterRoleBinding operations |
| `namespace` | Namespace provisioning operations |
| `credential` | Kubeconfig and secret operations |
| `system` | Generic system operations |

### Event Actions

| Action | Description |
|--------|-------------|
| `create` | Resource created |
| `update` | Resource updated |
| `delete` | Resource deleted |
| `bind` | Role binding created |
| `unbind` | Role binding removed |
| `grant` | Permission granted |
| `revoke` | Permission revoked |
| `sync` | Resource synchronized |
| `error` | Operation failed |

## Cluster Activity Audit (Kubernetes Native)

To track what users actually **do** with their permissions (kubectl commands, API calls, etc.), you need Kubernetes API server audit logging.

### What It Tracks

- Authentication events (login attempts)
- All API requests (get, list, watch, create, update, delete)
- Who made the request (user/SA identity)
- What resource was accessed
- Request/response details

### Enabling API Server Audit Logging

#### 1. Create an Audit Policy

Create a policy that captures relevant events. Save as `/etc/kubernetes/audit-policy.yaml`:

```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  # Log authentication failures
  - level: Metadata
    omitStages:
      - RequestReceived
    resources:
      - group: "authentication.k8s.io"
        resources: ["tokenreviews"]
    verbs: ["create"]

  # Log all actions by operator-managed ServiceAccounts
  # ServiceAccounts created by the operator follow the naming pattern: <user-name>
  - level: RequestResponse
    users:
      - system:serviceaccount:*:*  # All ServiceAccounts
    verbs: ["create", "update", "patch", "delete"]
    omitStages:
      - RequestReceived

  # Log read operations at Metadata level (less verbose)
  - level: Metadata
    users:
      - system:serviceaccount:*:*
    verbs: ["get", "list", "watch"]
    omitStages:
      - RequestReceived

  # Log secrets access (sensitive)
  - level: Metadata
    resources:
      - group: ""
        resources: ["secrets"]
    omitStages:
      - RequestReceived

  # Log RBAC changes
  - level: RequestResponse
    resources:
      - group: "rbac.authorization.k8s.io"
        resources: ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
    omitStages:
      - RequestReceived

  # Log k8s-iam-operator CRD changes
  - level: RequestResponse
    resources:
      - group: "k8sio.auth"
        resources: ["users", "groups", "roles"]
    omitStages:
      - RequestReceived

  # Catch-all: log everything else at Metadata level
  - level: Metadata
    omitStages:
      - RequestReceived
```

#### 2. Configure the API Server

Add these flags to your kube-apiserver configuration:

```yaml
# For kubeadm clusters, edit /etc/kubernetes/manifests/kube-apiserver.yaml
spec:
  containers:
  - command:
    - kube-apiserver
    - --audit-policy-file=/etc/kubernetes/audit-policy.yaml
    - --audit-log-path=/var/log/kubernetes/audit/audit.log
    - --audit-log-maxage=30
    - --audit-log-maxbackup=10
    - --audit-log-maxsize=100
    volumeMounts:
    - mountPath: /etc/kubernetes/audit-policy.yaml
      name: audit-policy
      readOnly: true
    - mountPath: /var/log/kubernetes/audit
      name: audit-log
  volumes:
  - hostPath:
      path: /etc/kubernetes/audit-policy.yaml
      type: File
    name: audit-policy
  - hostPath:
      path: /var/log/kubernetes/audit
      type: DirectoryOrCreate
    name: audit-log
```

For managed Kubernetes (EKS, GKE, AKS), refer to your provider's documentation:
- **EKS**: Enable via CloudWatch audit logs
- **GKE**: Enabled by default, viewable in Cloud Logging
- **AKS**: Enable via Azure Monitor

#### 3. Audit Log Format

Kubernetes audit logs look like this:

```json
{
  "kind": "Event",
  "apiVersion": "audit.k8s.io/v1",
  "level": "RequestResponse",
  "auditID": "abc-123",
  "stage": "ResponseComplete",
  "requestURI": "/api/v1/namespaces/default/pods",
  "verb": "create",
  "user": {
    "username": "system:serviceaccount:iam:developer-alice",
    "groups": ["system:serviceaccounts", "system:serviceaccounts:iam"]
  },
  "objectRef": {
    "resource": "pods",
    "namespace": "default",
    "name": "my-app"
  },
  "responseStatus": {
    "code": 201
  },
  "requestReceivedTimestamp": "2024-01-15T10:30:00.000000Z",
  "stageTimestamp": "2024-01-15T10:30:00.100000Z"
}
```

## Grafana Audit Dashboard

The operator includes a pre-built Grafana dashboard for visualizing user/ServiceAccount activity from Kubernetes API audit logs.

### Prerequisites

1. **Loki** deployed in your cluster
2. **Kubernetes API audit logs** shipped to Loki
3. **Grafana** with Loki datasource configured

### Enable the Dashboard

```yaml
# values.yaml
grafanaAuditDashboard:
  enabled: true
  labels:
    grafana_dashboard: "1"
```

### Dashboard Panels

The audit dashboard includes:

| Panel | Description |
|-------|-------------|
| **Total API Calls** | Count of API requests by ServiceAccounts |
| **Failed Requests** | Requests with 4xx/5xx status codes |
| **Forbidden (403)** | Permission denied attempts |
| **Active ServiceAccounts** | Unique SAs making API calls |
| **API Calls by ServiceAccount** | Time series of activity per SA |
| **API Calls by Verb** | Breakdown: get, list, create, delete, etc. |
| **Top Resources Accessed** | Most accessed resource types |
| **Activity by Target Namespace** | Which namespaces are being accessed |
| **Forbidden Requests by User** | Who is getting permission denied |
| **Sensitive Resource Modifications** | Changes to secrets, RBAC, etc. |
| **Live Audit Log** | Real-time log stream |

### Shipping Audit Logs to Loki

#### Option 1: Promtail (Recommended)

```yaml
# promtail-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: promtail-config
data:
  promtail.yaml: |
    server:
      http_listen_port: 9080

    positions:
      filename: /tmp/positions.yaml

    clients:
      - url: http://loki:3100/loki/api/v1/push

    scrape_configs:
      # Kubernetes API server audit logs
      - job_name: kube-apiserver-audit
        static_configs:
          - targets:
              - localhost
            labels:
              job: kube-apiserver-audit
              __path__: /var/log/kubernetes/audit/audit.log

      # k8s-iam-operator logs
      - job_name: k8s-iam-operator
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app_kubernetes_io_name]
            regex: k8s-iam-operator
            action: keep
          - source_labels: [__meta_kubernetes_namespace]
            target_label: namespace
          - source_labels: [__meta_kubernetes_pod_name]
            target_label: pod
        pipeline_stages:
          - json:
              expressions:
                category: category
                action: action
                outcome: outcome
          - labels:
              category:
              action:
              outcome:
```

#### Option 2: Fluent Bit to Loki

```yaml
# fluent-bit-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  fluent-bit.conf: |
    [SERVICE]
        Parsers_File parsers.conf

    [INPUT]
        Name              tail
        Path              /var/log/kubernetes/audit/audit.log
        Parser            json
        Tag               kube.audit
        Refresh_Interval  5

    [OUTPUT]
        Name              loki
        Match             kube.audit
        Host              loki
        Port              3100
        Labels            job=kube-apiserver-audit

  parsers.conf: |
    [PARSER]
        Name        json
        Format      json
        Time_Key    requestReceivedTimestamp
        Time_Format %Y-%m-%dT%H:%M:%S.%fZ
```

### Loki Label Configuration

For optimal query performance, ensure these labels are extracted:

```yaml
# In your Promtail pipeline or Loki config
pipeline_stages:
  - json:
      expressions:
        verb: verb
        user_username: user.username
        objectRef_resource: objectRef.resource
        objectRef_namespace: objectRef.namespace
        responseStatus_code: responseStatus.code
  - labels:
      verb:
      user_username:
      objectRef_resource:
      objectRef_namespace:
      responseStatus_code:
```

### Example Queries

**All activity by a specific user:**
```logql
{job="kube-apiserver-audit"} | json | user_username="system:serviceaccount:iam:alice"
```

**Failed requests in the last hour:**
```logql
{job="kube-apiserver-audit"} | json | responseStatus_code >= 400
```

**Secret access attempts:**
```logql
{job="kube-apiserver-audit"} | json | objectRef_resource="secrets"
```

**Delete operations:**
```logql
{job="kube-apiserver-audit"} | json | verb="delete"
```

## Correlating Audit Logs

### Linking Operator Users to API Activity

The operator creates ServiceAccounts with the same name as the User CRD:

| User CRD | ServiceAccount | API Server Identity |
|----------|----------------|---------------------|
| `developer-alice` | `developer-alice` | `system:serviceaccount:<namespace>:developer-alice` |

To correlate:

1. **Operator audit log**: Shows when user `developer-alice` was created
2. **K8s audit log**: Shows API calls by `system:serviceaccount:iam:developer-alice`

### Example Query (Elasticsearch/OpenSearch)

```json
{
  "query": {
    "bool": {
      "should": [
        {
          "match": {
            "subject.name": "developer-alice"
          }
        },
        {
          "match": {
            "user.username": "system:serviceaccount:iam:developer-alice"
          }
        }
      ]
    }
  },
  "sort": [
    { "@timestamp": "desc" }
  ]
}
```

### Example Query (Loki/Grafana)

```logql
{namespace="iam"} |~ "developer-alice"
  | json
  | line_format "{{.timestamp}} {{.action}} {{.subject.name}}"
```

## Log Aggregation

### Recommended Stack

For production environments, aggregate both operator and API server audit logs:

```
┌─────────────────────┐     ┌─────────────────────┐
│  Operator Logs      │     │  API Server Logs    │
│  (stdout/JSON)      │     │  (/var/log/audit)   │
└─────────┬───────────┘     └─────────┬───────────┘
          │                           │
          ▼                           ▼
┌─────────────────────────────────────────────────┐
│              Log Shipper                        │
│  (Fluent Bit / Fluentd / Vector / Filebeat)    │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│           Log Storage & Analysis                │
│  (Elasticsearch / Loki / Splunk / Datadog)     │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│              Visualization                      │
│  (Grafana / Kibana / Splunk UI)                │
└─────────────────────────────────────────────────┘
```

### Fluent Bit Configuration Example

```yaml
# fluent-bit-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  fluent-bit.conf: |
    [SERVICE]
        Parsers_File parsers.conf

    # Collect operator audit logs
    [INPUT]
        Name              tail
        Path              /var/log/containers/k8s-iam-operator*.log
        Parser            docker
        Tag               iam.operator.*
        Refresh_Interval  5

    # Collect API server audit logs
    [INPUT]
        Name              tail
        Path              /var/log/kubernetes/audit/audit.log
        Parser            json
        Tag               k8s.audit.*
        Refresh_Interval  5

    # Output to Elasticsearch
    [OUTPUT]
        Name              es
        Match             *
        Host              elasticsearch
        Port              9200
        Index             kubernetes-audit
        Type              _doc

  parsers.conf: |
    [PARSER]
        Name        docker
        Format      json
        Time_Key    time
        Time_Format %Y-%m-%dT%H:%M:%S.%L
```

### Security Tools Integration

For advanced security monitoring, consider:

- **Falco**: Runtime security monitoring
- **Tetragon**: eBPF-based observability
- **Sysdig**: Container security platform

These tools can alert on suspicious activity patterns detected in audit logs.

## Compliance Considerations

### SOC 2 / ISO 27001

Enable both audit log sources to satisfy:
- **Access Control**: Track who has access (operator logs)
- **Activity Monitoring**: Track what users do (API server logs)
- **Change Management**: Track permission changes (both)

### Log Retention

Configure retention based on compliance requirements:

```yaml
# API Server
--audit-log-maxage=365      # Days to retain
--audit-log-maxbackup=100   # Number of files to keep
--audit-log-maxsize=100     # Size in MB per file
```

### Immutability

Send logs to immutable storage (S3 with Object Lock, WORM storage) to prevent tampering.
