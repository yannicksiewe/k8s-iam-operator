"""Kopf event handlers for k8s-iam-operator.

This module registers all CRD handlers with Kopf and provides
optional OpenTelemetry tracing support.
"""

import kopf
import os
import logging

from app.config import Config
from app.utils.audit import configure_audit_logging
from .user_handlers import create_user_handler, update_user_handler, delete_user_handler
from .role_handlers import create_role_handler, delete_role_handler
from .group_handlers import create_group_handler, update_group_handler, delete_group_handler

logger = logging.getLogger(__name__)

# Configure audit logging
configure_audit_logging()

# Setup tracer if enabled
tracer = None
if os.environ.get('ENABLE_TRACING', 'False').lower() == 'true':
    try:
        from app.utils.tracing import setup_tracer
        tracer = setup_tracer()
        logger.info("OpenTelemetry tracing enabled")
    except Exception as e:
        logger.warning(f"Failed to initialize tracing: {e}")


def with_tracing(handler):
    """Decorator to add tracing to handlers."""
    def wrapper(*args, **kwargs):
        if tracer:
            with tracer.start_as_current_span(handler.__name__):
                return handler(*args, **kwargs)
        return handler(*args, **kwargs)
    return wrapper


# ==================== Group Handlers ====================

@kopf.on.create(Config.GROUP, Config.VERSION, Config.GPLURAL)
@with_tracing
def create_group_fn(body, spec, **kwargs):
    """Handle Group creation."""
    return create_group_handler(body, spec, **kwargs)


@kopf.on.update(Config.GROUP, Config.VERSION, Config.GPLURAL)
@with_tracing
def update_group_fn(body, spec, **kwargs):
    """Handle Group update."""
    return update_group_handler(body, spec, **kwargs)


@kopf.on.delete(Config.GROUP, Config.VERSION, Config.GPLURAL)
@with_tracing
def delete_group_fn(body, **kwargs):
    """Handle Group deletion."""
    return delete_group_handler(body, **kwargs)


# ==================== Role/ClusterRole Handlers ====================

@kopf.on.create(Config.GROUP, Config.VERSION, Config.RPLURAL)
@kopf.on.create(Config.GROUP, Config.VERSION, Config.CRPLURAL)
@kopf.on.update(Config.GROUP, Config.VERSION, Config.RPLURAL)
@kopf.on.update(Config.GROUP, Config.VERSION, Config.CRPLURAL)
@with_tracing
def create_role_fn(spec, **kwargs):
    """Handle Role/ClusterRole creation or update."""
    return create_role_handler(spec, **kwargs)


@kopf.on.delete(Config.GROUP, Config.VERSION, Config.RPLURAL)
@kopf.on.delete(Config.GROUP, Config.VERSION, Config.CRPLURAL)
@with_tracing
def delete_role_fn(**kwargs):
    """Handle Role/ClusterRole deletion."""
    return delete_role_handler(**kwargs)


# ==================== User Handlers ====================

@kopf.on.create(Config.GROUP, Config.VERSION, Config.PLURAL)
@with_tracing
def create_user_fn(body, spec, **kwargs):
    """Handle User creation."""
    return create_user_handler(body, spec, **kwargs)


@kopf.on.update(Config.GROUP, Config.VERSION, Config.PLURAL)
@with_tracing
def update_user_fn(body, spec, **kwargs):
    """Handle User update."""
    return update_user_handler(body, spec, **kwargs)


@kopf.on.delete(Config.GROUP, Config.VERSION, Config.PLURAL)
@with_tracing
def delete_user_fn(body, spec, **kwargs):
    """Handle User deletion."""
    return delete_user_handler(body, spec, **kwargs)


def main():
    """Start the Kopf operator."""
    logger.info("Starting k8s-iam-operator")
    kopf.run()
