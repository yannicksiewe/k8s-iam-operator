"""Configuration management for k8s-iam-operator.

This module provides clean configuration management using environment
variables with sensible defaults.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OperatorConfig:
    """Operator configuration from environment variables."""

    # CRD configuration
    group: str = os.environ.get('GROUP_NAME', 'k8sio.auth')
    version: str = os.environ.get('VERSION', 'v1')
    user_plural: str = os.environ.get('PLURAL', 'users')
    group_plural: str = os.environ.get('GROUP_PLURAL', 'groups')
    role_plural: str = os.environ.get('ROLE_PLURAL', 'roles')
    cluster_role_plural: str = os.environ.get('CLUSTER_ROLE_PLURAL', 'clusterroles')

    # Tracing configuration
    tracing_enabled: bool = os.environ.get('ENABLE_TRACING', 'False').lower() == 'true'
    tempo_endpoint: str = os.environ.get('TEMPO_ENDPOINT', 'http://localhost:4317/')

    # Logging configuration
    log_level: str = os.environ.get('LOG_LEVEL', 'INFO')
    log_format: str = os.environ.get('LOG_FORMAT', 'json')

    # Operator settings
    audit_enabled: bool = os.environ.get('AUDIT_ENABLED', 'True').lower() == 'true'


# Backwards compatible Config class
class Config:
    """Legacy configuration class for backwards compatibility."""

    GROUP = os.environ.get('GROUP_NAME', 'k8sio.auth')
    VERSION = os.environ.get('VERSION', 'v1')
    PLURAL = os.environ.get('PLURAL', 'users')
    GPLURAL = os.environ.get('GROUP_PLURAL', 'groups')
    RPLURAL = os.environ.get('ROLE_PLURAL', 'roles')
    CRPLURAL = os.environ.get('CLUSTER_ROLE_PLURAL', 'clusterroles')
    TEMPO_ENDPOINT = os.environ.get('TEMPO_ENDPOINT', 'http://localhost:4317/')


def get_config() -> OperatorConfig:
    """Get the operator configuration.

    Returns:
        OperatorConfig instance with current configuration
    """
    return OperatorConfig()
