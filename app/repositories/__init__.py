"""Repository layer for Kubernetes API abstraction.

This module provides repository classes that abstract Kubernetes API calls,
making the business logic layer testable with mocked repositories.
"""

from app.repositories.base import BaseRepository
from app.repositories.namespace_repository import NamespaceRepository
from app.repositories.serviceaccount_repository import ServiceAccountRepository
from app.repositories.secret_repository import SecretRepository
from app.repositories.rbac_repository import RBACRepository

__all__ = [
    "BaseRepository",
    "NamespaceRepository",
    "ServiceAccountRepository",
    "SecretRepository",
    "RBACRepository",
]
