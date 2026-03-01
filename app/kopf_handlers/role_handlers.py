"""Role and ClusterRole CRD event handlers.

This module provides thin Kopf handlers that delegate to the RoleService.
"""

import logging

from app.container import get_container
from app.exceptions import OperatorError, ValidationError

logger = logging.getLogger(__name__)


def create_role_handler(spec: dict, **kwargs) -> dict:
    """Handle Role/ClusterRole CRD creation or update.

    Args:
        spec: The spec portion of the CRD
        **kwargs: Additional Kopf kwargs (includes body, namespace, name, etc.)

    Returns:
        Status dict for Kopf
    """
    body = kwargs.get('body', {})
    namespace = kwargs.get('namespace', 'default')

    try:
        container = get_container()
        result = container.role_service.create_role(body, spec, namespace)
        return result
    except ValidationError as e:
        logger.error(f"Validation error creating role: {e.message}")
        return {"error": e.message, "field": e.field}
    except OperatorError as e:
        logger.error(f"Error creating role: {e.message}")
        return {"error": e.message}
    except Exception as e:
        logger.exception(f"Unexpected error creating role: {str(e)}")
        return {"error": str(e)}


def delete_role_handler(**kwargs) -> dict:
    """Handle Role/ClusterRole CRD deletion.

    Args:
        **kwargs: Kopf kwargs (includes body, namespace, name, etc.)

    Returns:
        Status dict for Kopf
    """
    body = kwargs.get('body', {})
    namespace = kwargs.get('namespace', 'default')

    try:
        container = get_container()
        result = container.role_service.delete_role(body, namespace)
        return result
    except OperatorError as e:
        logger.error(f"Error deleting role: {e.message}")
        return {"error": e.message}
    except Exception as e:
        logger.exception(f"Unexpected error deleting role: {str(e)}")
        return {"error": str(e)}
