"""Prometheus metrics endpoint for k8s-iam-operator.

This module provides the /metrics endpoint for Prometheus scraping
and metric recording functions for IAM operations.
"""

from flask import Blueprint, Response
from prometheus_client import (
    generate_latest,
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
)

metrics_bp = Blueprint('metrics', __name__)

# ==================== Operator Info ====================

OPERATOR_INFO = Info(
    'k8s_iam_operator',
    'Information about the k8s-iam-operator'
)

# ==================== User Metrics ====================

USERS_TOTAL = Gauge(
    'k8s_iam_operator_users_total',
    'Total number of users by type',
    ['namespace', 'user_type']  # user_type: human, serviceAccount
)

USERS_CREATED = Counter(
    'k8s_iam_operator_users_created_total',
    'Total number of users created',
    ['namespace', 'user_type']
)

USERS_DELETED = Counter(
    'k8s_iam_operator_users_deleted_total',
    'Total number of users deleted',
    ['namespace', 'user_type']
)

USER_OPERATIONS = Counter(
    'k8s_iam_operator_user_operations_total',
    'Total user operations',
    ['operation', 'user_type', 'outcome']  # outcome: success, failure
)

# ==================== Group Metrics ====================

GROUPS_TOTAL = Gauge(
    'k8s_iam_operator_groups_total',
    'Total number of groups',
    ['namespace']
)

GROUPS_CREATED = Counter(
    'k8s_iam_operator_groups_created_total',
    'Total number of groups created',
    ['namespace']
)

GROUPS_DELETED = Counter(
    'k8s_iam_operator_groups_deleted_total',
    'Total number of groups deleted',
    ['namespace']
)

# ==================== Role Metrics ====================

ROLES_TOTAL = Gauge(
    'k8s_iam_operator_roles_total',
    'Total number of custom roles',
    ['namespace', 'kind']  # kind: Role, ClusterRole
)

ROLES_CREATED = Counter(
    'k8s_iam_operator_roles_created_total',
    'Total number of roles created',
    ['namespace', 'kind']
)

ROLES_DELETED = Counter(
    'k8s_iam_operator_roles_deleted_total',
    'Total number of roles deleted',
    ['namespace', 'kind']
)

# ==================== RBAC Binding Metrics ====================

ROLE_BINDINGS_TOTAL = Gauge(
    'k8s_iam_operator_role_bindings_total',
    'Total number of role bindings managed',
    ['namespace', 'kind']  # kind: RoleBinding, ClusterRoleBinding
)

ROLE_BINDINGS_CREATED = Counter(
    'k8s_iam_operator_role_bindings_created_total',
    'Total number of role bindings created',
    ['namespace', 'kind']
)

ROLE_BINDINGS_DELETED = Counter(
    'k8s_iam_operator_role_bindings_deleted_total',
    'Total number of role bindings deleted',
    ['namespace', 'kind']
)

# ==================== Namespace Metrics ====================

NAMESPACES_CREATED = Counter(
    'k8s_iam_operator_namespaces_created_total',
    'Total namespaces created for users',
    ['network_policy']  # none, isolated, restricted
)

NAMESPACES_DELETED = Counter(
    'k8s_iam_operator_namespaces_deleted_total',
    'Total namespaces deleted'
)

NAMESPACE_QUOTAS_APPLIED = Counter(
    'k8s_iam_operator_namespace_quotas_applied_total',
    'Total namespace quotas applied'
)

# ==================== Kubeconfig Metrics ====================

KUBECONFIGS_GENERATED = Counter(
    'k8s_iam_operator_kubeconfigs_generated_total',
    'Total kubeconfig secrets generated',
    ['namespace']
)

# ==================== Handler Metrics ====================

HANDLER_DURATION = Histogram(
    'k8s_iam_operator_handler_duration_seconds',
    'Handler execution duration in seconds',
    ['handler', 'action'],  # action: create, update, delete
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

HANDLER_ERRORS = Counter(
    'k8s_iam_operator_handler_errors_total',
    'Total number of handler errors',
    ['handler', 'error_type']
)

# ==================== Reconciliation Metrics ====================

RECONCILIATION_TOTAL = Counter(
    'k8s_iam_operator_reconciliations_total',
    'Total reconciliation attempts',
    ['resource_type', 'action', 'outcome']
)

RECONCILIATION_DURATION = Histogram(
    'k8s_iam_operator_reconciliation_duration_seconds',
    'Reconciliation duration in seconds',
    ['resource_type', 'action'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

# ==================== Legacy Gauges (for compatibility) ====================

ACTIVE_USERS = Gauge(
    'k8s_iam_operator_active_users',
    'Number of active users (deprecated, use users_total)',
    ['namespace']
)

ACTIVE_GROUPS = Gauge(
    'k8s_iam_operator_active_groups',
    'Number of active groups (deprecated, use groups_total)',
    ['namespace']
)


# ==================== Endpoints ====================

@metrics_bp.route('/actuator/metrics')
def metrics() -> Response:
    """Prometheus metrics endpoint.

    Returns:
        Response with Prometheus metrics
    """
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@metrics_bp.route('/metrics')
def metrics_short() -> Response:
    """Shortened metrics endpoint.

    Returns:
        Response with Prometheus metrics
    """
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# ==================== Recording Functions ====================

def set_operator_info(version: str, python_version: str = "") -> None:
    """Set operator info metric."""
    info = {"version": version}
    if python_version:
        info["python_version"] = python_version
    OPERATOR_INFO.info(info)


# User metrics
def record_user_created(namespace: str, user_type: str = "serviceAccount") -> None:
    """Record a user creation."""
    USERS_CREATED.labels(namespace=namespace, user_type=user_type).inc()
    USER_OPERATIONS.labels(
        operation="create", user_type=user_type, outcome="success"
    ).inc()


def record_user_deleted(namespace: str, user_type: str = "serviceAccount") -> None:
    """Record a user deletion."""
    USERS_DELETED.labels(namespace=namespace, user_type=user_type).inc()
    USER_OPERATIONS.labels(
        operation="delete", user_type=user_type, outcome="success"
    ).inc()


def record_user_error(
    operation: str, user_type: str = "serviceAccount", error_type: str = "unknown"
) -> None:
    """Record a user operation error."""
    USER_OPERATIONS.labels(
        operation=operation, user_type=user_type, outcome="failure"
    ).inc()
    HANDLER_ERRORS.labels(handler="user", error_type=error_type).inc()


def set_users_total(namespace: str, user_type: str, count: int) -> None:
    """Set total users gauge."""
    USERS_TOTAL.labels(namespace=namespace, user_type=user_type).set(count)


# Group metrics
def record_group_created(namespace: str) -> None:
    """Record a group creation."""
    GROUPS_CREATED.labels(namespace=namespace).inc()


def record_group_deleted(namespace: str) -> None:
    """Record a group deletion."""
    GROUPS_DELETED.labels(namespace=namespace).inc()


def set_groups_total(namespace: str, count: int) -> None:
    """Set total groups gauge."""
    GROUPS_TOTAL.labels(namespace=namespace).set(count)


def set_roles_total(namespace: str, kind: str, count: int) -> None:
    """Set total roles gauge."""
    ROLES_TOTAL.labels(namespace=namespace, kind=kind).set(count)


# Role metrics
def record_role_created(namespace: str, kind: str) -> None:
    """Record a role creation."""
    ROLES_CREATED.labels(namespace=namespace, kind=kind).inc()


def record_role_deleted(namespace: str, kind: str) -> None:
    """Record a role deletion."""
    ROLES_DELETED.labels(namespace=namespace, kind=kind).inc()


# RBAC binding metrics
def record_role_binding_created(namespace: str, kind: str) -> None:
    """Record a role binding creation."""
    ROLE_BINDINGS_CREATED.labels(namespace=namespace, kind=kind).inc()


def record_role_binding_deleted(namespace: str, kind: str) -> None:
    """Record a role binding deletion."""
    ROLE_BINDINGS_DELETED.labels(namespace=namespace, kind=kind).inc()


# Namespace metrics
def record_namespace_created(network_policy: str = "none") -> None:
    """Record a namespace creation."""
    NAMESPACES_CREATED.labels(network_policy=network_policy).inc()


def record_namespace_deleted() -> None:
    """Record a namespace deletion."""
    NAMESPACES_DELETED.inc()


def record_quota_applied() -> None:
    """Record a quota application."""
    NAMESPACE_QUOTAS_APPLIED.inc()


# Kubeconfig metrics
def record_kubeconfig_generated(namespace: str) -> None:
    """Record kubeconfig generation."""
    KUBECONFIGS_GENERATED.labels(namespace=namespace).inc()


# Handler metrics
def record_handler_error(handler: str, error_type: str) -> None:
    """Record a handler error."""
    HANDLER_ERRORS.labels(handler=handler, error_type=error_type).inc()


def observe_handler_duration(handler: str, action: str, duration: float) -> None:
    """Record handler execution duration."""
    HANDLER_DURATION.labels(handler=handler, action=action).observe(duration)


# Reconciliation metrics
def record_reconciliation(
    resource_type: str, action: str, outcome: str, duration: float
) -> None:
    """Record a reconciliation attempt."""
    RECONCILIATION_TOTAL.labels(
        resource_type=resource_type, action=action, outcome=outcome
    ).inc()
    RECONCILIATION_DURATION.labels(
        resource_type=resource_type, action=action
    ).observe(duration)
