"""Audit logging for RBAC changes.

This module provides structured audit logging for all RBAC-related
operations in the k8s-iam-operator.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger("audit")


class AuditLogger:
    """Structured audit logger for RBAC changes."""

    def __init__(self, operator_name: str = "k8s-iam-operator"):
        """Initialize the audit logger.

        Args:
            operator_name: Name of the operator for log entries
        """
        self.operator_name = operator_name

    def _log(self, action: str, resource_type: str, name: str,
             namespace: Optional[str] = None,
             details: Optional[Dict[str, Any]] = None) -> None:
        """Log an audit entry.

        Args:
            action: The action performed (CREATE, UPDATE, DELETE)
            resource_type: Type of resource affected
            name: Name of the resource
            namespace: Optional namespace of the resource
            details: Optional additional details
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": self.operator_name,
            "action": action,
            "resource": {
                "type": resource_type,
                "name": name,
            }
        }

        if namespace:
            entry["resource"]["namespace"] = namespace

        if details:
            entry["details"] = details

        # Log as JSON for easy parsing by log aggregation systems
        logger.info(json.dumps(entry))

    def log_create(self, resource_type: str, name: str,
                   namespace: Optional[str] = None,
                   details: Optional[Dict[str, Any]] = None) -> None:
        """Log a resource creation.

        Args:
            resource_type: Type of resource created
            name: Name of the resource
            namespace: Optional namespace
            details: Optional additional details
        """
        self._log("CREATE", resource_type, name, namespace, details)

    def log_update(self, resource_type: str, name: str,
                   namespace: Optional[str] = None,
                   details: Optional[Dict[str, Any]] = None) -> None:
        """Log a resource update.

        Args:
            resource_type: Type of resource updated
            name: Name of the resource
            namespace: Optional namespace
            details: Optional additional details
        """
        self._log("UPDATE", resource_type, name, namespace, details)

    def log_delete(self, resource_type: str, name: str,
                   namespace: Optional[str] = None,
                   details: Optional[Dict[str, Any]] = None) -> None:
        """Log a resource deletion.

        Args:
            resource_type: Type of resource deleted
            name: Name of the resource
            namespace: Optional namespace
            details: Optional additional details
        """
        self._log("DELETE", resource_type, name, namespace, details)

    def log_binding_create(self, binding_type: str, name: str,
                           subject_name: str, subject_kind: str,
                           role_name: str, namespace: Optional[str] = None) -> None:
        """Log a role binding creation with detailed subject/role info.

        Args:
            binding_type: Type of binding (RoleBinding, ClusterRoleBinding)
            name: Name of the binding
            subject_name: Name of the subject
            subject_kind: Kind of subject (ServiceAccount, Group, User)
            role_name: Name of the role being bound
            namespace: Optional namespace
        """
        self._log(
            "CREATE",
            binding_type,
            name,
            namespace,
            {
                "subject": {"name": subject_name, "kind": subject_kind},
                "role": role_name
            }
        )

    def log_binding_delete(self, binding_type: str, name: str,
                           namespace: Optional[str] = None,
                           reason: Optional[str] = None) -> None:
        """Log a role binding deletion.

        Args:
            binding_type: Type of binding (RoleBinding, ClusterRoleBinding)
            name: Name of the binding
            namespace: Optional namespace
            reason: Optional reason for deletion
        """
        details = {}
        if reason:
            details["reason"] = reason

        self._log("DELETE", binding_type, name, namespace, details or None)

    def log_error(self, operation: str, resource_type: str, name: str,
                  error: str, namespace: Optional[str] = None) -> None:
        """Log an error during an operation.

        Args:
            operation: The operation that failed
            resource_type: Type of resource
            name: Name of the resource
            error: Error message
            namespace: Optional namespace
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": self.operator_name,
            "action": "ERROR",
            "operation": operation,
            "resource": {
                "type": resource_type,
                "name": name,
            },
            "error": error
        }

        if namespace:
            entry["resource"]["namespace"] = namespace

        logger.error(json.dumps(entry))


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance.

    Returns:
        The global AuditLogger instance
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def configure_audit_logging(level: int = logging.INFO) -> None:
    """Configure the audit logger with appropriate handlers.

    Args:
        level: Logging level for audit logs
    """
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(level)

    # Use JSON formatter for audit logs
    handler = logging.StreamHandler()
    handler.setLevel(level)

    # Simple format - the message itself is already JSON
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)

    # Avoid duplicate handlers
    if not audit_logger.handlers:
        audit_logger.addHandler(handler)

    # Don't propagate to root logger to avoid double logging
    audit_logger.propagate = False
