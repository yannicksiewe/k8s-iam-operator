# Development Guide

This guide covers setting up a development environment for k8s-iam-operator.

## Prerequisites

- Python 3.9+
- Docker
- kind (Kubernetes in Docker)
- kubectl
- Helm 3.x
- make

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yannick-siewe/k8s-iam-operator.git
cd k8s-iam-operator

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
make install-deps

# Create kind cluster
make kind-create

# Install CRDs
make crds-install

# Run operator locally
make run
```

## Development Workflow

### Running Tests

```bash
# Run unit tests
make test

# Run with coverage report
make test-coverage

# Run integration tests (requires cluster)
make integration-test
```

### Linting

```bash
# Run all linters
make lint
```

### Building

```bash
# Build Docker image
make build

# Load into kind cluster
make kind-load
```

## Project Architecture

### Layer Diagram

```
┌─────────────────────────────────────────────┐
│            Kopf Handlers                     │
│         (app/kopf_handlers/)                 │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│            Service Layer                     │
│           (app/services/)                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│  │ User    │ │ Group   │ │ Role    │        │
│  │ Service │ │ Service │ │ Service │        │
│  └────┬────┘ └────┬────┘ └────┬────┘        │
│       │           │           │              │
│  ┌────▼───────────▼───────────▼────┐        │
│  │         RBAC Service             │        │
│  │      Kubeconfig Service          │        │
│  └──────────────┬───────────────────┘        │
└─────────────────┼───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│          Repository Layer                    │
│         (app/repositories/)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │Namespace │ │ Service  │ │  RBAC    │     │
│  │  Repo    │ │Account   │ │  Repo    │     │
│  └────┬─────┘ │  Repo    │ └────┬─────┘     │
│       │       └────┬─────┘      │            │
└───────┼────────────┼────────────┼───────────┘
        │            │            │
┌───────▼────────────▼────────────▼───────────┐
│          Kubernetes API                      │
└─────────────────────────────────────────────┘
```

### Key Components

**Handlers** (`app/kopf_handlers/`)
- Thin wrappers for Kopf events
- Delegate to services
- Handle errors and return status

**Services** (`app/services/`)
- Business logic layer
- Orchestrate repository calls
- Validation and error handling

**Repositories** (`app/repositories/`)
- Kubernetes API abstraction
- Consistent error handling
- Testable with mocks

**Models** (`app/models/`)
- Dataclasses for CRD resources
- Serialization/deserialization
- Type safety

### Dependency Injection

Services receive dependencies via constructor:

```python
class UserService:
    def __init__(
        self,
        sa_repo: ServiceAccountRepository,
        ns_repo: NamespaceRepository,
        rbac_service: RBACService,
        kubeconfig_service: KubeconfigService,
    ):
        self.sa_repo = sa_repo
        # ...
```

The `ServiceContainer` (`app/container.py`) wires dependencies:

```python
container = get_container()
user_service = container.user_service
```

## Testing Strategy

### Unit Tests

- Mock all repositories
- Test services in isolation
- Use fixtures from `conftest.py`

```python
def test_create_user(user_service, mock_sa_repo):
    result = user_service.create_user(body, spec, "default")
    mock_sa_repo.create.assert_called_once()
```

### Integration Tests

- Use real kind cluster
- Test full CRD lifecycle
- Verify actual resources created

```python
@pytest.mark.integration
def test_user_lifecycle(custom_api, core_api):
    # Create User CRD
    custom_api.create_namespaced_custom_object(...)

    # Verify ServiceAccount created
    sa = core_api.read_namespaced_service_account(...)
```

## Adding a New Feature

1. **Define the model** in `app/models/`
2. **Add validation** in `app/validators.py`
3. **Create repository methods** if needed
4. **Implement service logic** in `app/services/`
5. **Update handler** in `app/kopf_handlers/`
6. **Write unit tests**
7. **Write integration tests**
8. **Update documentation**

## Debugging

### Local Debugging

```bash
# Run with debug logging
LOG_LEVEL=DEBUG make run
```

### In-Cluster Debugging

```bash
# Get operator logs
kubectl logs -n iam -l app.kubernetes.io/name=k8s-iam-operator -f

# Check events
kubectl get events -n iam

# Describe operator pod
kubectl describe pod -n iam -l app.kubernetes.io/name=k8s-iam-operator
```

### Common Issues

**CRDs not found**
```bash
make crds-install
```

**Permission denied**
```bash
kubectl auth can-i --list --as=system:serviceaccount:iam:k8s-iam-operator
```

**Resource not processed**
- Check operator logs for errors
- Verify CRD spec is valid
- Check referenced resources exist

## IDE Setup

### VS Code

Recommended extensions:
- Python
- Pylance
- Docker
- Kubernetes

`.vscode/settings.json`:
```json
{
    "python.linting.flake8Enabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"]
}
```

### PyCharm

- Set interpreter to `.venv/bin/python`
- Configure pytest as test runner
- Enable flake8 inspections
