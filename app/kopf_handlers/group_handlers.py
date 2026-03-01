"""Group CRD event handlers.

This module provides thin Kopf handlers that delegate to the GroupService.
"""

import logging

from app.container import get_container
from app.exceptions import OperatorError, ValidationError

logger = logging.getLogger(__name__)


def create_group_handler(body: dict, spec, **kwargs) -> dict:
    """Handle Group CRD creation.

    Args:
        body: The full Kopf body object
        spec: The spec portion of the CRD (may be kopf.Body)
        **kwargs: Additional Kopf kwargs (includes namespace, name, etc.)

    Returns:
        Status dict for Kopf
    """
    namespace = kwargs.get('namespace', 'default')
    spec_dict = dict(spec) if spec else {}

    try:
        container = get_container()
        result = container.group_service.create_group(dict(body), spec_dict, namespace)
        return result
    except ValidationError as e:
        logger.error(f"Validation error creating group: {e.message}")
        return {"error": e.message, "field": e.field}
    except OperatorError as e:
        logger.error(f"Error creating group: {e.message}")
        return {"error": e.message}
    except Exception as e:
        logger.exception(f"Unexpected error creating group: {str(e)}")
        return {"error": str(e)}


def update_group_handler(body: dict, spec, **kwargs) -> dict:
    """Handle Group CRD update.

    Args:
        body: The full Kopf body object
        spec: The spec portion of the CRD (may be kopf.Body)
        **kwargs: Additional Kopf kwargs

    Returns:
        Status dict for Kopf
    """
    namespace = kwargs.get('namespace', 'default')
    spec_dict = dict(spec) if spec else {}

    try:
        container = get_container()
        result = container.group_service.update_group(dict(body), spec_dict, namespace)
        return result
    except ValidationError as e:
        logger.error(f"Validation error updating group: {e.message}")
        return {"error": e.message, "field": e.field}
    except OperatorError as e:
        logger.error(f"Error updating group: {e.message}")
        return {"error": e.message}
    except Exception as e:
        logger.exception(f"Unexpected error updating group: {str(e)}")
        return {"error": str(e)}


def delete_group_handler(body, **kwargs) -> dict:
    """Handle Group CRD deletion.

    Args:
        body: The full Kopf body object (may be kopf.Body)
        **kwargs: Additional Kopf kwargs

    Returns:
        Status dict for Kopf
    """
    namespace = kwargs.get('namespace', 'default')

    try:
        container = get_container()
        result = container.group_service.delete_group(dict(body), namespace)
        return result
    except OperatorError as e:
        logger.error(f"Error deleting group: {e.message}")
        return {"error": e.message}
    except Exception as e:
        logger.exception(f"Unexpected error deleting group: {str(e)}")
        return {"error": str(e)}
