# API Reference

This document describes the Custom Resource Definitions (CRDs) provided by k8s-iam-operator.

## User

A User resource creates a Kubernetes ServiceAccount with RBAC bindings.

### Spec

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | No | If true, creates user namespace and kubeconfig. Default: false |
| `CRoles` | array | No | List of ClusterRole bindings |
| `Roles` | array | No | List of Role names to bind |

### CRoles Entry

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `namespace` | string | Yes | Namespace for the RoleBinding |
| `clusterRole` | string | Yes | Name of the ClusterRole to bind |
| `group` | string | No | Optional group to include in the binding |

### Example

```yaml
apiVersion: k8sio.auth/v1
kind: User
metadata:
  name: developer
  namespace: iam
spec:
  enabled: true
  CRoles:
    - namespace: dev
      clusterRole: edit
    - namespace: staging
      clusterRole: view
      group: developers
  Roles:
    - custom-role
```

### Created Resources

When a User is created, the operator creates:

1. **ServiceAccount** - In the User's namespace
2. **Service Account Token Secret** - If enabled
3. **User Namespace** - If enabled, named same as user
4. **Kubeconfig Secret** - If enabled, in user namespace
5. **RoleBindings** - For each CRole entry
6. **Restricted ClusterRole** - If enabled, limits namespace access

---

## Group

A Group resource creates RBAC bindings for a Kubernetes Group.

### Spec

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `CRoles` | array | No | List of ClusterRole bindings |
| `Roles` | array | No | List of Role names to bind |

### CRoles Entry

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `namespace` | string | No | Namespace for binding (omit for cluster-wide) |
| `clusterRole` | string | Yes | Name of the ClusterRole to bind |

### Example

```yaml
apiVersion: k8sio.auth/v1
kind: Group
metadata:
  name: devops
  namespace: iam
spec:
  CRoles:
    # Namespaced binding
    - namespace: production
      clusterRole: view
    # Cluster-wide binding
    - clusterRole: cluster-view
  Roles:
    - custom-role
```

### Created Resources

1. **RoleBindings** - For CRoles with namespace
2. **ClusterRoleBindings** - For CRoles without namespace

---

## Role

A Role resource creates a Kubernetes Role.

### Spec

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rules` | array | Yes | List of RBAC policy rules |

### Rule Entry

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `apiGroups` | array | Yes | API groups (use "" for core) |
| `resources` | array | Yes | Resource types |
| `verbs` | array | Yes | Allowed operations |
| `resourceNames` | array | No | Specific resource names |

### Example

```yaml
apiVersion: k8sio.auth/v1
kind: Role
metadata:
  name: pod-reader
  namespace: default
spec:
  rules:
    - apiGroups: [""]
      resources: ["pods"]
      verbs: ["get", "list", "watch"]
    - apiGroups: ["apps"]
      resources: ["deployments"]
      verbs: ["get", "list"]
```

---

## ClusterRole

A ClusterRole resource creates a Kubernetes ClusterRole.

### Spec

Same as Role, but applies cluster-wide.

### Example

```yaml
apiVersion: k8sio.auth/v1
kind: ClusterRole
metadata:
  name: namespace-viewer
spec:
  rules:
    - apiGroups: [""]
      resources: ["namespaces"]
      verbs: ["get", "list", "watch"]
```

---

## Valid Verbs

The following RBAC verbs are supported:

- `get` - Read a single resource
- `list` - List resources
- `watch` - Watch for changes
- `create` - Create resources
- `update` - Update resources
- `patch` - Patch resources
- `delete` - Delete a single resource
- `deletecollection` - Delete multiple resources
- `use` - Use a resource (PodSecurityPolicy)
- `bind` - Bind to a role
- `escalate` - Escalate privileges
- `impersonate` - Impersonate users/groups
- `*` - All verbs

---

## Naming Conventions

### RoleBinding Names

For Users:
```
{user-name}-{namespace}-{clusterRole}
```

For Groups with namespace:
```
{group-name}-{namespace}-{clusterRole}
```

### ClusterRoleBinding Names

For Groups cluster-wide:
```
{group-name}-{group-namespace}-{clusterRole}
```

### User Resources

- ServiceAccount: `{user-name}`
- Token Secret: `{user-name}-token`
- Kubeconfig Secret: `{user-name}-cluster-config`
- User Namespace: `{user-name}`
- Restricted Role: `{user-name}-restricted-namespace-role`
