"""Custom exceptions for k8s-iam-operator.

This module defines a hierarchy of exceptions for clean error handling
across the operator codebase.
"""

import re
from typing import Optional, Any, Set


# Sensitive field names that should be redacted in logs and error messages
SENSITIVE_FIELDS: Set[str] = {
    'token',
    'password',
    'secret',
    'kubeconfig',
    'ca_cert',
    'ca_data',
    'client_certificate',
    'client_key',
    'bearer_token',
    'api_key',
    'credentials',
    'private_key',
    'auth',
    'authorization',
}

# Pattern to match sensitive data in strings (e.g., base64-encoded tokens)
SENSITIVE_PATTERNS = [
    # Bearer tokens
    (re.compile(r'(Bearer\s+)[A-Za-z0-9+/=_-]+', re.IGNORECASE), r'\1[REDACTED]'),
    # Base64-encoded data (long strings)
    (re.compile(r'(["\']?)([A-Za-z0-9+/]{50,}=*)\1'), r'\1[REDACTED]\1'),
    # Kubernetes tokens
    (re.compile(r'(token["\s:=]+)[A-Za-z0-9._-]+', re.IGNORECASE), r'\1[REDACTED]'),
]


def sanitize_value(value: Any, field_name: str = '') -> Any:
    """Sanitize a value by redacting sensitive information.

    Args:
        value: The value to sanitize
        field_name: Optional field name to check against sensitive fields

    Returns:
        Sanitized value with sensitive data redacted
    """
    # Check if field name indicates sensitive data
    field_lower = field_name.lower()
    for sensitive in SENSITIVE_FIELDS:
        if sensitive in field_lower:
            if isinstance(value, str) and len(value) > 0:
                return '[REDACTED]'
            elif isinstance(value, (bytes, bytearray)):
                return '[REDACTED]'

    # For strings, apply pattern-based redaction
    if isinstance(value, str):
        result = value
        for pattern, replacement in SENSITIVE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    # For dictionaries, recursively sanitize
    if isinstance(value, dict):
        return sanitize_dict(value)

    # For lists, sanitize each element
    if isinstance(value, (list, tuple)):
        return [sanitize_value(item) for item in value]

    return value


def sanitize_dict(data: dict) -> dict:
    """Sanitize a dictionary by redacting sensitive fields.

    Args:
        data: Dictionary that may contain sensitive information

    Returns:
        New dictionary with sensitive values redacted
    """
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        result[key] = sanitize_value(value, key)
    return result


def sanitize_message(message: str) -> str:
    """Sanitize an error message by redacting sensitive patterns.

    Args:
        message: Error message that may contain sensitive data

    Returns:
        Message with sensitive data redacted
    """
    result = message
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


class OperatorError(Exception):
    """Base exception for all operator errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = sanitize_message(message)
        self.details = sanitize_dict(details or {})
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for logging/API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:
        """Return sanitized string representation."""
        return self.message

    def __repr__(self) -> str:
        """Return sanitized repr."""
        return f"{self.__class__.__name__}({self.message!r})"


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
