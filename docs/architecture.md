# Architecture Deep-Dive

This document provides a comprehensive overview of the k8s-iam-operator architecture, design decisions, and internal workings.

## Table of Contents

- [Overview](#overview)
- [Component Diagram](#component-diagram)
- [Data Flow](#data-flow)
- [Core Components](#core-components)
- [Design Decisions](#design-decisions)
- [Extension Points](#extension-points)

## Overview

The k8s-iam-operator is a Kubernetes operator that manages Identity and Access Management (IAM) through Custom Resource Definitions (CRDs). It automates the creation and management of:

- ServiceAccounts
- RoleBindings and ClusterRoleBindings
- Kubeconfig generation for external access

### Key Characteristics

- **Declarative**: Users define desired state through CRDs
- **Reconciliation-based**: Continuously ensures actual state matches desired state
- **Event-driven**: Responds to Kubernetes API events
- **Idempotent**: Safe to run multiple times without side effects

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Kubernetes Cluster                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         k8s-iam-operator                                 ││
│  │                                                                          ││
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                 ││
│  │  │   Kopf       │   │   Flask      │   │  Metrics     │                 ││
│  │  │  Handlers    │   │    API       │   │  Exporter    │                 ││
│  │  │              │   │              │   │              │                 ││
│  │  │ • user_      │   │ /actuator/   │   │ prometheus_  │                 ││
│  │  │   handler    │   │   health     │   │   client     │                 ││
│  │  │ • group_     │   │ /actuator/   │   │              │                 ││
│  │  │   handler    │   │   metrics    │   │              │                 ││
│  │  │ • role_      │   │              │   │              │                 ││
│  │  │   handler    │   │              │   │              │                 ││
│  │  └──────┬───────┘   └──────────────┘   └──────────────┘                 ││
│  │         │                                                                ││
│  │  ┌──────▼──────────────────────────────────────────────────────────────┐││
│  │  │                          Services Layer                              │││
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │││
│  │  │  │ UserService  │  │ GroupService │  │ RoleService  │               │││
│  │  │  │              │  │              │  │              │               │││
│  │  │  │ • create     │  │ • create     │  │ • create     │               │││
│  │  │  │ • update     │  │ • update     │  │ • update     │               │││
│  │  │  │ • delete     │  │ • delete     │  │ • delete     │               │││
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘               │││
│  │  │                                                                      │││
│  │  │  ┌──────────────┐  ┌──────────────┐                                 │││
│  │  │  │ RBACService  │  │ Kubeconfig   │                                 │││
│  │  │  │              │  │   Service    │                                 │││
│  │  │  │ • bind_role  │  │              │                                 │││
│  │  │  │ • unbind     │  │ • generate   │                                 │││
│  │  │  └──────────────┘  └──────────────┘                                 │││
│  │  └──────────────────────────────────────────────────────────────────────┘││
│  │         │                                                                ││
│  │  ┌──────▼──────────────────────────────────────────────────────────────┐││
│  │  │                        Repository Layer                              │││
│  │  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │││
│  │  │  │  Namespace     │  │ ServiceAccount │  │     RBAC       │         │││
│  │  │  │  Repository    │  │  Repository    │  │   Repository   │         │││
│  │  │  └────────────────┘  └────────────────┘  └────────────────┘         │││
│  │  │  ┌────────────────┐                                                  │││
│  │  │  │    Secret      │                                                  │││
│  │  │  │  Repository    │                                                  │││
│  │  │  └────────────────┘                                                  │││
│  │  └──────────────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                       Kubernetes API Server                              ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ││
│  │  │  Users   │  │  Groups  │  │  Roles   │  │ Service  │  │   RBAC   │  ││
│  │  │  (CRD)   │  │  (CRD)   │  │  (CRD)   │  │ Accounts │  │ Bindings │  ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘

                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │         External Systems            │
                    │  ┌───────────┐    ┌───────────┐    │
                    │  │Prometheus │    │  Jaeger/  │    │
                    │  │           │    │   Tempo   │    │
                    │  └───────────┘    └───────────┘    │
                    └─────────────────────────────────────┘
```

## Data Flow

### User Creation Flow

```
1. User creates User CR
   │
   ▼
2. Kubernetes API stores CR
   │
   ▼
3. Kopf receives CREATE event
   │
   ▼
4. user_handler.create() called
   │
   ├───► 5a. Validate spec
   │
   ├───► 5b. Create ServiceAccount
   │          (via ServiceAccountRepository)
   │
   ├───► 5c. Create ServiceAccount token secret
   │          (via SecretRepository)
   │
   ├───► 5d. Create RoleBindings for each namespace
   │          (via RBACService)
   │
   ├───► 5e. Generate kubeconfig
   │          (via KubeconfigService)
   │
   └───► 5f. Store kubeconfig as Secret
              (via SecretRepository)
   │
   ▼
6. Update User CR status
   │
   ▼
7. User can retrieve kubeconfig
```

### Reconciliation Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                     Reconciliation Loop                          │
│                                                                  │
│  ┌─────────┐     ┌─────────────┐     ┌─────────────┐            │
│  │ Watch   │────►│   Event     │────►│   Handler   │            │
│  │ Events  │     │   Queue     │     │  Execution  │            │
│  └─────────┘     └─────────────┘     └──────┬──────┘            │
│                                              │                   │
│                                              ▼                   │
│                                     ┌───────────────┐            │
│                                     │    Success?   │            │
│                                     └───────┬───────┘            │
│                                             │                    │
│                              ┌──────────────┴──────────────┐     │
│                              │                             │     │
│                              ▼                             ▼     │
│                     ┌───────────────┐            ┌────────────┐ │
│                     │ Update Status │            │   Retry    │ │
│                     │    Success    │            │ with Backoff│ │
│                     └───────────────┘            └────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### Kopf Framework

[Kopf](https://kopf.readthedocs.io/) (Kubernetes Operator Pythonic Framework) provides:

- **Event watching**: Monitors CRD changes
- **Handler registration**: Decorators for create/update/delete events
- **Retry logic**: Automatic retry with exponential backoff
- **Status management**: Tracks handler execution state

```python
@kopf.on.create('k8sio.auth', 'v1', 'users')
def user_create_handler(spec, name, namespace, **kwargs):
    # Handler logic
    pass
```

### Services Layer

Services encapsulate business logic and orchestrate repository calls.

#### UserService
- Creates user identity (ServiceAccount)
- Manages user's role bindings
- Orchestrates kubeconfig generation

#### GroupService
- Manages group membership
- Applies group-level role bindings
- Handles group hierarchy

#### RoleService
- Creates custom roles
- Maps to Kubernetes Roles/ClusterRoles

#### RBACService
- Creates RoleBindings and ClusterRoleBindings
- Manages subject-to-role mappings

#### KubeconfigService
- Generates kubeconfig files
- Handles cluster CA and endpoint configuration
- Manages token embedding

### Repository Layer

Repositories provide a clean abstraction over Kubernetes API calls.

```python
class NamespaceRepository:
    def exists(self, name: str) -> bool: ...
    def create(self, name: str, labels: dict) -> V1Namespace: ...
    def ensure_exists(self, name: str) -> V1Namespace: ...

class ServiceAccountRepository:
    def get(self, name: str, namespace: str) -> V1ServiceAccount: ...
    def create(self, name: str, namespace: str) -> V1ServiceAccount: ...
    def delete(self, name: str, namespace: str) -> None: ...

class RBACRepository:
    def create_role_binding(self, ...) -> V1RoleBinding: ...
    def create_cluster_role_binding(self, ...) -> V1ClusterRoleBinding: ...
```

### Custom Resource Definitions

#### User CRD
```yaml
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: john-doe
spec:
  roleRef: developer       # Reference to ClusterRole or Role CRD
  namespaces:              # Namespaces where user has access
    - development
    - staging
  generateKubeconfig: true # Whether to generate kubeconfig
status:
  phase: Ready
  serviceAccount: john-doe
  kubeconfigSecret: john-doe-kubeconfig
```

#### Group CRD
```yaml
apiVersion: k8sio.auth/v1
kind: Group
metadata:
  name: developers
spec:
  roleRef: developer
  namespaces:
    - development
  members:                 # List of User references
    - john-doe
    - jane-doe
```

#### Role CRD
```yaml
apiVersion: k8sio.auth/v1
kind: Role
metadata:
  name: developer
spec:
  clusterRole: true        # Create ClusterRole vs Role
  rules:
    - apiGroups: [""]
      resources: ["pods", "services"]
      verbs: ["get", "list", "watch", "create", "update"]
```

## Design Decisions

### Why Kopf?

1. **Pythonic**: Native Python with async support
2. **Lightweight**: No heavy dependencies
3. **Built-in features**: Retry, status, events
4. **Active community**: Well-maintained

Alternatives considered:
- Operator SDK (Go): Steeper learning curve
- Kubebuilder (Go): More boilerplate
- Metacontroller: Limited flexibility

### Repository Pattern

**Decision**: Use repository pattern for Kubernetes API access

**Rationale**:
- Testability: Easy to mock in unit tests
- Separation of concerns: Business logic independent of API details
- Error handling: Centralized API error handling
- Reusability: Share repository instances across services

### Service-Oriented Architecture

**Decision**: Separate services for each domain concept

**Rationale**:
- Single responsibility: Each service handles one concept
- Composability: Services can call other services
- Testing: Easier unit testing with focused services

### Kubeconfig as Secret

**Decision**: Store generated kubeconfig as Kubernetes Secret

**Rationale**:
- Security: Secrets are encrypted at rest
- Access control: RBAC controls who can read secrets
- Portability: Standard Kubernetes pattern
- Rotation: Easy to regenerate and update

### Event-Driven vs Polling

**Decision**: Use Kubernetes watch events (event-driven)

**Rationale**:
- Efficiency: No wasted API calls
- Responsiveness: Immediate reaction to changes
- Scalability: Better with many resources
- Built-in: Kopf handles watch management

## Extension Points

### Adding New CRDs

1. Define CRD in `crd/` directory
2. Create model in `app/models/`
3. Create service in `app/services/`
4. Create handlers in `app/kopf_handlers/`
5. Update RBAC permissions

### Adding New Services

```python
# app/services/my_service.py
class MyService:
    def __init__(self, repository: MyRepository):
        self._repository = repository

    def my_operation(self, name: str) -> Result:
        # Business logic
        pass
```

### Custom Validators

```python
# app/validators.py
def validate_my_field(value: str) -> bool:
    # Validation logic
    return True
```

### Webhooks (Future)

Admission webhooks can be added for:
- Validation: Reject invalid resources before storage
- Mutation: Modify resources before storage
- Conversion: Handle CRD version upgrades

## Performance Considerations

### Caching

- Kopf caches watched resources
- Repository layer can implement caching if needed
- Use informers for frequently accessed resources

### Batching

- Group related operations when possible
- Use patch operations instead of full updates
- Consider bulk operations for mass changes

### Resource Limits

- Set appropriate memory/CPU limits
- Monitor for memory leaks
- Scale horizontally with HPA

## Security Architecture

### RBAC Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    Operator ServiceAccount                       │
│                                                                  │
│  Has ClusterRole with permissions to:                           │
│  • Read/Write CRDs (users, groups, roles)                       │
│  • Create/Delete ServiceAccounts                                │
│  • Create/Delete RoleBindings/ClusterRoleBindings               │
│  • Create/Delete Secrets                                        │
│  • Read Namespaces                                              │
└─────────────────────────────────────────────────────────────────┘
         │
         │ grants
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Managed ServiceAccounts                       │
│                                                                  │
│  • One per User CRD                                             │
│  • Limited to specified namespaces                              │
│  • Permissions from referenced Role CRD                         │
└─────────────────────────────────────────────────────────────────┘
```

### Trust Boundaries

1. **Operator → API Server**: Secured via ServiceAccount token
2. **API Server → etcd**: Secured via TLS + authentication
3. **Users → API Server**: Via generated kubeconfig with limited permissions

## Monitoring Integration

### Metrics Exposed

| Metric | Type | Description |
|--------|------|-------------|
| `kopf_handler_duration_seconds` | Histogram | Handler execution time |
| `kopf_handler_errors_total` | Counter | Handler errors |
| `http_requests_total` | Counter | HTTP requests to API |
| `http_request_duration_seconds` | Histogram | HTTP request duration |

### Tracing Integration

OpenTelemetry integration provides:
- Distributed trace context
- Span for each handler execution
- Integration with Jaeger/Tempo

### Logging Structure

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "handler": "user_create_handler",
  "resource": "users/john-doe",
  "message": "User created successfully",
  "trace_id": "abc123"
}
```
