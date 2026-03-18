"""Namespace event handlers for k8s-iam-operator.

This module watches for namespace creation events and triggers
reconciliation of Users/Groups that have role bindings targeting
those namespaces. This ensures that when a namespace is deleted
and recreated, the RoleBindings are automatically restored.
"""

import logging
from kubernetes import client
from kubernetes.client.rest import ApiException

from app.config import Config
from app.container import get_container
from app.models.user import User
from app.models.group import Group

logger = logging.getLogger(__name__)


def namespace_created_handler(name: str, **kwargs) -> None:
    """Handle namespace creation events.

    When a namespace is created, find all Users and Groups that have
    CRoles targeting that namespace and reconcile their RoleBindings.

    Args:
        name: The name of the created namespace
        **kwargs: Additional Kopf kwargs
    """
    logger.info(f"Namespace '{name}' created, checking for Users/Groups to reconcile")

    try:
        container = get_container()
        custom_api = client.CustomObjectsApi()

        # Find and reconcile Users
        _reconcile_users_for_namespace(custom_api, container, name)

        # Find and reconcile Groups
        _reconcile_groups_for_namespace(custom_api, container, name)

    except Exception as e:
        logger.exception(f"Error reconciling bindings for namespace '{name}': {e}")


def _reconcile_users_for_namespace(
    custom_api: client.CustomObjectsApi,
    container,
    namespace: str
) -> None:
    """Find and reconcile Users that target the given namespace.

    Args:
        custom_api: Kubernetes CustomObjectsApi client
        container: Dependency injection container
        namespace: The namespace to reconcile for
    """
    try:
        # List all Users across all namespaces
        users = custom_api.list_cluster_custom_object(
            group=Config.GROUP,
            version=Config.VERSION,
            plural=Config.PLURAL
        )

        reconciled_count = 0
        for user_dict in users.get('items', []):
            user_name = user_dict.get('metadata', {}).get('name', 'unknown')
            spec = user_dict.get('spec', {})
            c_roles = spec.get('CRoles', [])

            # Check if any CRole targets this namespace
            targets_namespace = any(
                cr.get('namespace') == namespace
                for cr in c_roles
            )

            if targets_namespace:
                logger.info(
                    f"Reconciling User '{user_name}' for namespace '{namespace}'"
                )
                try:
                    user = User.from_dict(user_dict)
                    container.rbac_service.create_user_role_bindings(user)
                    reconciled_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to reconcile User '{user_name}': {e}"
                    )

        if reconciled_count > 0:
            logger.info(
                f"Reconciled {reconciled_count} User(s) for namespace '{namespace}'"
            )

    except ApiException as e:
        if e.status == 404:
            logger.debug("No User CRDs found in cluster")
        else:
            logger.error(f"Error listing Users: {e}")
    except Exception as e:
        logger.error(f"Error reconciling Users for namespace '{namespace}': {e}")


def _reconcile_groups_for_namespace(
    custom_api: client.CustomObjectsApi,
    container,
    namespace: str
) -> None:
    """Find and reconcile Groups that target the given namespace.

    Args:
        custom_api: Kubernetes CustomObjectsApi client
        container: Dependency injection container
        namespace: The namespace to reconcile for
    """
    try:
        # List all Groups across all namespaces
        groups = custom_api.list_cluster_custom_object(
            group=Config.GROUP,
            version=Config.VERSION,
            plural=Config.GPLURAL
        )

        reconciled_count = 0
        for group_dict in groups.get('items', []):
            group_name = group_dict.get('metadata', {}).get('name', 'unknown')
            spec = group_dict.get('spec', {})
            c_roles = spec.get('CRoles', [])

            # Check if any CRole targets this namespace
            targets_namespace = any(
                cr.get('namespace') == namespace
                for cr in c_roles
            )

            if targets_namespace:
                logger.info(
                    f"Reconciling Group '{group_name}' for namespace '{namespace}'"
                )
                try:
                    group = Group.from_dict(group_dict)
                    container.rbac_service.create_group_role_bindings(group)
                    reconciled_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to reconcile Group '{group_name}': {e}"
                    )

        if reconciled_count > 0:
            logger.info(
                f"Reconciled {reconciled_count} Group(s) for namespace '{namespace}'"
            )

    except ApiException as e:
        if e.status == 404:
            logger.debug("No Group CRDs found in cluster")
        else:
            logger.error(f"Error listing Groups: {e}")
    except Exception as e:
        logger.error(f"Error reconciling Groups for namespace '{namespace}': {e}")
