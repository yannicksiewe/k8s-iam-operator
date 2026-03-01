"""Prometheus metrics endpoint for k8s-iam-operator.

This module provides the /metrics endpoint for Prometheus scraping.
"""

from flask import Blueprint, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Gauge, Histogram

metrics_bp = Blueprint('metrics', __name__)

# Define custom metrics
USERS_CREATED = Counter(
    'k8s_iam_operator_users_created_total',
    'Total number of users created',
    ['namespace']
)

USERS_DELETED = Counter(
    'k8s_iam_operator_users_deleted_total',
    'Total number of users deleted',
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

HANDLER_ERRORS = Counter(
    'k8s_iam_operator_handler_errors_total',
    'Total number of handler errors',
    ['handler', 'error_type']
)

HANDLER_DURATION = Histogram(
    'k8s_iam_operator_handler_duration_seconds',
    'Handler execution duration in seconds',
    ['handler'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_USERS = Gauge(
    'k8s_iam_operator_active_users',
    'Number of active users',
    ['namespace']
)

ACTIVE_GROUPS = Gauge(
    'k8s_iam_operator_active_groups',
    'Number of active groups',
    ['namespace']
)


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


# Helper functions for recording metrics
def record_user_created(namespace: str) -> None:
    """Record a user creation."""
    USERS_CREATED.labels(namespace=namespace).inc()


def record_user_deleted(namespace: str) -> None:
    """Record a user deletion."""
    USERS_DELETED.labels(namespace=namespace).inc()


def record_group_created(namespace: str) -> None:
    """Record a group creation."""
    GROUPS_CREATED.labels(namespace=namespace).inc()


def record_group_deleted(namespace: str) -> None:
    """Record a group deletion."""
    GROUPS_DELETED.labels(namespace=namespace).inc()


def record_role_created(namespace: str, kind: str) -> None:
    """Record a role creation."""
    ROLES_CREATED.labels(namespace=namespace, kind=kind).inc()


def record_role_deleted(namespace: str, kind: str) -> None:
    """Record a role deletion."""
    ROLES_DELETED.labels(namespace=namespace, kind=kind).inc()


def record_handler_error(handler: str, error_type: str) -> None:
    """Record a handler error."""
    HANDLER_ERRORS.labels(handler=handler, error_type=error_type).inc()


def observe_handler_duration(handler: str, duration: float) -> None:
    """Record handler execution duration."""
    HANDLER_DURATION.labels(handler=handler).observe(duration)
