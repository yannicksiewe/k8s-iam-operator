"""Custom exceptions for k8s-iam-operator.

This module defines a hierarchy of exceptions for clean error handling
across the operator codebase.
"""

from typing import Optional, Any


class OperatorError(Exception):
    """Base exception for all operator errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for logging/API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(OperatorError):
    """Raised when input validation fails."""

    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.value = value
        details = {"field": field}
        if value is not None:
            details["value"] = str(value)[:100]  # Truncate for safety
        super().__init__(message=message, details=details)


class ResourceNotFoundError(OperatorError):
    """Raised when a Kubernetes resource is not found."""

    def __init__(self, resource_type: str, name: str, namespace: Optional[str] = None):
        self.resource_type = resource_type
        self.name = name
        self.namespace = namespace
        details = {"resource_type": resource_type, "name": name}
        if namespace:
            details["namespace"] = namespace
        message = f"{resource_type} '{name}' not found"
        if namespace:
            message += f" in namespace '{namespace}'"
        super().__init__(message=message, details=details)


class ResourceAlreadyExistsError(OperatorError):
    """Raised when attempting to create a resource that already exists."""

    def __init__(self, resource_type: str, name: str, namespace: Optional[str] = None):
        self.resource_type = resource_type
        self.name = name
        self.namespace = namespace
        details = {"resource_type": resource_type, "name": name}
        if namespace:
            details["namespace"] = namespace
        message = f"{resource_type} '{name}' already exists"
        if namespace:
            message += f" in namespace '{namespace}'"
        super().__init__(message=message, details=details)


class KubernetesAPIError(OperatorError):
    """Raised when a Kubernetes API call fails."""

    def __init__(self, operation: str, message: str, status_code: Optional[int] = None):
        self.operation = operation
        self.status_code = status_code
        details = {"operation": operation}
        if status_code:
            details["status_code"] = status_code
        super().__init__(message=message, details=details)


class RBACError(OperatorError):
    """Raised for RBAC-related errors."""

    def __init__(self, message: str, binding_name: Optional[str] = None, role_name: Optional[str] = None):
        details = {}
        if binding_name:
            details["binding_name"] = binding_name
        if role_name:
            details["role_name"] = role_name
        super().__init__(message=message, details=details)


class ConfigurationError(OperatorError):
    """Raised when there's a configuration error."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message=message, details=details)


class KubeconfigGenerationError(OperatorError):
    """Raised when kubeconfig generation fails."""

    def __init__(self, user_name: str, message: str):
        self.user_name = user_name
        details = {"user_name": user_name}
        super().__init__(message=message, details=details)


class ServiceAccountError(OperatorError):
    """Raised for service account related errors."""

    def __init__(self, sa_name: str, namespace: str, message: str):
        self.sa_name = sa_name
        self.namespace = namespace
        details = {"service_account": sa_name, "namespace": namespace}
        super().__init__(message=message, details=details)


class NamespaceError(OperatorError):
    """Raised for namespace related errors."""

    def __init__(self, namespace: str, message: str):
        self.namespace = namespace
        details = {"namespace": namespace}
        super().__init__(message=message, details=details)
