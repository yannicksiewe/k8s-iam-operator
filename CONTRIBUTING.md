# Contributing to k8s-iam-operator

Thank you for your interest in contributing to k8s-iam-operator! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.9+
- Docker
- Kubernetes cluster (kind recommended for local development)
- kubectl
- Helm 3.x

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yannick-siewe/k8s-iam-operator.git
cd k8s-iam-operator
```

2. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
make install-deps
```

4. Create a kind cluster for testing:
```bash
make kind-create
make crds-install
```

5. Run the operator locally:
```bash
make run
```

## Project Structure

```
k8s-iam-operator/
├── app/                    # Application code
│   ├── api/               # Flask health/metrics API
│   ├── handlers/          # Kopf event handlers
│   ├── models/            # Data models
│   ├── repositories/      # Kubernetes API abstraction
│   ├── services/          # Business logic layer
│   └── utils/             # Utilities (audit, logging)
├── charts/                # Helm chart
├── crd/                   # CRD definitions
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
└── docs/                  # Documentation
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Maximum line length: 100 characters
- Run linting before committing: `make lint`

## Testing

### Running Tests

```bash
# Run unit tests
make test

# Run with coverage
make test-coverage

# Run integration tests (requires cluster)
make integration-test
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use pytest fixtures from `tests/conftest.py`
- Mock Kubernetes API calls for unit tests
- Use real clusters for integration tests

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `make test`
5. Run linting: `make lint`
6. Commit with descriptive messages
7. Push to your fork
8. Create a Pull Request

### PR Requirements

- All tests must pass
- Code must pass linting
- New features should include tests
- Update documentation as needed

## Commit Messages

Use clear, descriptive commit messages:

```
feat: Add support for custom namespace labels
fix: Resolve race condition in role binding creation
docs: Update deployment instructions
test: Add tests for group service
refactor: Extract RBAC logic to service layer
```

## Architecture Guidelines

### Service Layer

Business logic should be in service classes:
- `UserService` - User lifecycle management
- `GroupService` - Group lifecycle management
- `RoleService` - Role/ClusterRole management
- `RBACService` - RBAC binding operations
- `KubeconfigService` - Kubeconfig generation

### Repository Layer

Kubernetes API operations should go through repositories:
- `NamespaceRepository`
- `ServiceAccountRepository`
- `SecretRepository`
- `RBACRepository`

### Handlers

Kopf handlers should be thin wrappers that delegate to services.

## Reporting Issues

When reporting issues, please include:
- Kubernetes version
- Operator version
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
