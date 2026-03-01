"""Data models for k8s-iam-operator.

This module provides dataclasses for representing User, Group, and Role
resources in a type-safe manner.
"""

from app.models.user import User, UserSpec, ClusterRoleBinding
from app.models.group import Group, GroupSpec
from app.models.role import Role, ClusterRole, RoleSpec, PolicyRule

__all__ = [
    "User",
    "UserSpec",
    "ClusterRoleBinding",
    "Group",
    "GroupSpec",
    "Role",
    "ClusterRole",
    "RoleSpec",
    "PolicyRule",
]
