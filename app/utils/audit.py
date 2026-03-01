"""Audit logging for IAM operations.

This module provides structured audit logging for all IAM-related
operations in the k8s-iam-operator.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
from contextvars import ContextVar

logger = logging.getLogger("audit")

# Context variable for trace ID (for distributed tracing)
_trace_id: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)


class EventCategory(str, Enum):
    """Category of IAM event."""
    USER = "user"
    GROUP = "group"
    ROLE = "role"
    RBAC = "rbac"
    NAMESPACE = "namespace"
    CREDENTIAL = "credential"
    SYSTEM = "system"


class EventAction(str, Enum):
    """Action type for IAM event."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BIND = "bind"
    UNBIND = "unbind"
    GRANT = "grant"
    REVOKE = "revoke"
    SYNC = "sync"
    ERROR = "error"


class EventOutcome(str, Enum):
    """Outcome of the event."""
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


@dataclass
class Actor:
    """Actor who initiated the event."""
    type: str  # operator, user, system
    name: str
    namespace: Optional[str] = None


@dataclass
class Subject:
    """Subject affected by the event."""
    type: str  # User, Group, ServiceAccount, Pod, etc.
    name: str
    namespace: Optional[str] = None
    uid: Optional[str] = None


@dataclass
class Resource:
    """Resource involved in the event."""
    type: str  # Role, ClusterRole, RoleBinding, etc.
    name: str
    namespace: Optional[str] = None
    api_version: str = "k8sio.auth/v1"


@dataclass
class IAMEvent:
    """Structured IAM audit event."""
    timestamp: str
    event_id: str
    category: EventCategory
    action: EventAction
    outcome: EventOutcome
    actor: Actor
    subject: Subject
    resource: Optional[Resource] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None
    duration_ms: Optional[float] = None
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        data = {
            "timestamp": self.timestamp,
            "event_id": self.event_id,
            "category": self.category.value,
            "action": self.action.value,
            "outcome": self.outcome.value,
            "actor": asdict(self.actor),
            "subject": asdict(self.subject),
            "message": self.message,
        }

        if self.resource:
            data["resource"] = asdict(self.resource)

        if self.details:
            data["details"] = self.details

        if self.trace_id:
            data["trace_id"] = self.trace_id

        if self.duration_ms is not None:
            data["duration_ms"] = self.duration_ms

        if self.labels:
            data["labels"] = self.labels

        return data

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """Structured audit logger for IAM operations."""

    def __init__(self, operator_name: str = "k8s-iam-operator"):
        """Initialize the audit logger.

        Args:
            operator_name: Name of the operator for log entries
        """
        self.operator_name = operator_name
        self._default_actor = Actor(type="operator", name=operator_name)

    def _get_trace_id(self) -> Optional[str]:
        """Get current trace ID from context."""
        return _trace_id.get()

    def _create_event(
        self,
        category: EventCategory,
        action: EventAction,
        outcome: EventOutcome,
        subject: Subject,
        resource: Optional[Resource] = None,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        actor: Optional[Actor] = None,
        duration_ms: Optional[float] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> IAMEvent:
        """Create an IAM event."""
        return IAMEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_id=str(uuid.uuid4()),
            category=category,
            action=action,
            outcome=outcome,
            actor=actor or self._default_actor,
            subject=subject,
            resource=resource,
            message=message,
            details=details or {},
            trace_id=self._get_trace_id(),
            duration_ms=duration_ms,
            labels=labels or {},
        )

    def _log_event(self, event: IAMEvent) -> None:
        """Log an event."""
        if event.outcome == EventOutcome.FAILURE:
            logger.error(event.to_json())
        else:
            logger.info(event.to_json())

    # ==================== User Events ====================

    def log_user_created(
        self,
        name: str,
        namespace: str,
        user_type: str,
        target_namespace: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log user creation."""
        event = self._create_event(
            category=EventCategory.USER,
            action=EventAction.CREATE,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type="User", name=name, namespace=namespace),
            message=f"Created {user_type} user '{name}'",
            details={
                "user_type": user_type,
                "target_namespace": target_namespace,
                **(details or {}),
            },
            labels={"user_type": user_type},
        )
        self._log_event(event)

    def log_user_updated(
        self,
        name: str,
        namespace: str,
        changes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log user update."""
        event = self._create_event(
            category=EventCategory.USER,
            action=EventAction.UPDATE,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type="User", name=name, namespace=namespace),
            message=f"Updated user '{name}'",
            details={"changes": changes} if changes else {},
        )
        self._log_event(event)

    def log_user_deleted(self, name: str, namespace: str) -> None:
        """Log user deletion."""
        event = self._create_event(
            category=EventCategory.USER,
            action=EventAction.DELETE,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type="User", name=name, namespace=namespace),
            message=f"Deleted user '{name}'",
        )
        self._log_event(event)

    # ==================== Group Events ====================

    def log_group_created(
        self,
        name: str,
        namespace: str,
        member_count: int = 0,
    ) -> None:
        """Log group creation."""
        event = self._create_event(
            category=EventCategory.GROUP,
            action=EventAction.CREATE,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type="Group", name=name, namespace=namespace),
            message=f"Created group '{name}'",
            details={"member_count": member_count},
        )
        self._log_event(event)

    def log_group_deleted(self, name: str, namespace: str) -> None:
        """Log group deletion."""
        event = self._create_event(
            category=EventCategory.GROUP,
            action=EventAction.DELETE,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type="Group", name=name, namespace=namespace),
            message=f"Deleted group '{name}'",
        )
        self._log_event(event)

    # ==================== RBAC Events ====================

    def log_role_binding_created(
        self,
        binding_name: str,
        binding_type: str,  # RoleBinding or ClusterRoleBinding
        subject_name: str,
        subject_kind: str,
        role_name: str,
        namespace: Optional[str] = None,
    ) -> None:
        """Log role binding creation."""
        event = self._create_event(
            category=EventCategory.RBAC,
            action=EventAction.BIND,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type=subject_kind, name=subject_name, namespace=namespace),
            resource=Resource(
                type=binding_type,
                name=binding_name,
                namespace=namespace,
                api_version="rbac.authorization.k8s.io/v1",
            ),
            message=f"Bound {subject_kind} '{subject_name}' to role '{role_name}'",
            details={"role": role_name, "binding_type": binding_type},
        )
        self._log_event(event)

    def log_role_binding_deleted(
        self,
        binding_name: str,
        binding_type: str,
        namespace: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Log role binding deletion."""
        event = self._create_event(
            category=EventCategory.RBAC,
            action=EventAction.UNBIND,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type=binding_type, name=binding_name, namespace=namespace),
            message=f"Deleted {binding_type} '{binding_name}'",
            details={"reason": reason} if reason else {},
        )
        self._log_event(event)

    # ==================== Namespace Events ====================

    def log_namespace_created(
        self,
        name: str,
        owner: str,
        quota: Optional[Dict[str, str]] = None,
        network_policy: Optional[str] = None,
    ) -> None:
        """Log namespace creation for user."""
        event = self._create_event(
            category=EventCategory.NAMESPACE,
            action=EventAction.CREATE,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type="Namespace", name=name),
            message=f"Created namespace '{name}' for user '{owner}'",
            details={
                "owner": owner,
                "quota": quota,
                "network_policy": network_policy,
            },
        )
        self._log_event(event)

    def log_namespace_deleted(self, name: str, owner: str) -> None:
        """Log namespace deletion."""
        event = self._create_event(
            category=EventCategory.NAMESPACE,
            action=EventAction.DELETE,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type="Namespace", name=name),
            message=f"Deleted namespace '{name}' (owner: {owner})",
            details={"owner": owner},
        )
        self._log_event(event)

    # ==================== ServiceAccount Events ====================

    def log_serviceaccount_created(
        self,
        name: str,
        namespace: str,
        user: str,
    ) -> None:
        """Log ServiceAccount creation."""
        event = self._create_event(
            category=EventCategory.USER,
            action=EventAction.CREATE,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type="ServiceAccount", name=name, namespace=namespace),
            message=f"Created ServiceAccount '{name}' for user '{user}'",
            details={"user": user},
        )
        self._log_event(event)

    def log_kubeconfig_generated(
        self,
        user: str,
        namespace: str,
        secret_name: str,
    ) -> None:
        """Log kubeconfig generation."""
        event = self._create_event(
            category=EventCategory.USER,
            action=EventAction.CREATE,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type="Secret", name=secret_name, namespace=namespace),
            message=f"Generated kubeconfig for user '{user}'",
            details={"user": user, "secret_type": "kubeconfig"},
            labels={"secret_type": "kubeconfig"},
        )
        self._log_event(event)

    # ==================== Generic Events ====================

    def log_create(
        self,
        resource_type: str,
        name: str,
        namespace: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a generic resource creation."""
        event = self._create_event(
            category=EventCategory.SYSTEM,
            action=EventAction.CREATE,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type=resource_type, name=name, namespace=namespace),
            message=f"Created {resource_type} '{name}'",
            details=details or {},
        )
        self._log_event(event)

    def log_update(
        self,
        resource_type: str,
        name: str,
        namespace: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a generic resource update."""
        event = self._create_event(
            category=EventCategory.SYSTEM,
            action=EventAction.UPDATE,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type=resource_type, name=name, namespace=namespace),
            message=f"Updated {resource_type} '{name}'",
            details=details or {},
        )
        self._log_event(event)

    def log_delete(
        self,
        resource_type: str,
        name: str,
        namespace: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a generic resource deletion."""
        event = self._create_event(
            category=EventCategory.SYSTEM,
            action=EventAction.DELETE,
            outcome=EventOutcome.SUCCESS,
            subject=Subject(type=resource_type, name=name, namespace=namespace),
            message=f"Deleted {resource_type} '{name}'",
            details=details or {},
        )
        self._log_event(event)

    # ==================== Error Events ====================

    def log_error(
        self,
        operation: str,
        resource_type: str,
        name: str,
        error: str,
        namespace: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an error during an operation."""
        event = self._create_event(
            category=EventCategory.SYSTEM,
            action=EventAction.ERROR,
            outcome=EventOutcome.FAILURE,
            subject=Subject(type=resource_type, name=name, namespace=namespace),
            message=f"Error during {operation} on {resource_type} '{name}': {error}",
            details={"operation": operation, "error": error, **(details or {})},
        )
        self._log_event(event)

    # ==================== Legacy Methods (backward compatibility) ====================

    def log_binding_create(
        self,
        binding_type: str,
        name: str,
        subject_name: str,
        subject_kind: str,
        role_name: str,
        namespace: Optional[str] = None,
    ) -> None:
        """Legacy method for role binding creation."""
        self.log_role_binding_created(
            binding_name=name,
            binding_type=binding_type,
            subject_name=subject_name,
            subject_kind=subject_kind,
            role_name=role_name,
            namespace=namespace,
        )

    def log_binding_delete(
        self,
        binding_type: str,
        name: str,
        namespace: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Legacy method for role binding deletion."""
        self.log_role_binding_deleted(
            binding_name=name,
            binding_type=binding_type,
            namespace=namespace,
            reason=reason,
        )


# ==================== Context Management ====================

def set_trace_id(trace_id: str) -> None:
    """Set trace ID for the current context."""
    _trace_id.set(trace_id)


def get_trace_id() -> Optional[str]:
    """Get trace ID from the current context."""
    return _trace_id.get()


def generate_trace_id() -> str:
    """Generate a new trace ID."""
    return str(uuid.uuid4())


# ==================== Global Instance ====================

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
