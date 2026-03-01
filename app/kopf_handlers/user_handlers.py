"""User CRD event handlers.

This module provides thin Kopf handlers that delegate to the UserService.
"""

import logging

from app.container import get_container
from app.exceptions import OperatorError, ValidationError

logger = logging.getLogger(__name__)


def create_user_handler(body: dict, spec: dict, **kwargs) -> dict:
    """Handle User CRD creation.

    Args:
        body: The full Kopf body object
        spec: The spec portion of the CRD
        **kwargs: Additional Kopf kwargs (includes namespace, name, etc.)

    Returns:
        Status dict for Kopf
    """
    namespace = kwargs.get('namespace', 'default')

    try:
        container = get_container()
        result = container.user_service.create_user(body, spec, namespace)
        return result
    except ValidationError as e:
        logger.error(f"Validation error creating user: {e.message}")
        return {"error": e.message, "field": e.field}
    except OperatorError as e:
        logger.error(f"Error creating user: {e.message}")
        return {"error": e.message}
    except Exception as e:
        logger.exception(f"Unexpected error creating user: {str(e)}")
        return {"error": str(e)}


def update_user_handler(body: dict, spec: dict, **kwargs) -> dict:
    """Handle User CRD update.

    Args:
        body: The full Kopf body object
        spec: The spec portion of the CRD
        **kwargs: Additional Kopf kwargs

    Returns:
        Status dict for Kopf
    """
    namespace = kwargs.get('namespace', 'default')

    try:
        container = get_container()
        result = container.user_service.update_user(body, spec, namespace)
        return result
    except ValidationError as e:
        logger.error(f"Validation error updating user: {e.message}")
        return {"error": e.message, "field": e.field}
    except OperatorError as e:
        logger.error(f"Error updating user: {e.message}")
        return {"error": e.message}
    except Exception as e:
        logger.exception(f"Unexpected error updating user: {str(e)}")
        return {"error": str(e)}


def delete_user_handler(body: dict, spec: dict, **kwargs) -> dict:
    """Handle User CRD deletion.

    Args:
        body: The full Kopf body object
        spec: The spec portion of the CRD
        **kwargs: Additional Kopf kwargs

    Returns:
        Status dict for Kopf
    """
    namespace = kwargs.get('namespace', 'default')

    try:
        container = get_container()
        result = container.user_service.delete_user(body, spec, namespace)
        return result
    except OperatorError as e:
        logger.error(f"Error deleting user: {e.message}")
        return {"error": e.message}
    except Exception as e:
        logger.exception(f"Unexpected error deleting user: {str(e)}")
        return {"error": str(e)}
