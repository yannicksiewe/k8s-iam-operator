"""Input validation for k8s-iam-operator.

This module provides validation functions for CRD inputs,
ensuring DNS compliance and security constraints.
"""

import re
from typing import List, Optional, Set

from app.exceptions import ValidationError


# DNS-1123 label constraints
DNS_LABEL_MAX_LENGTH = 63
DNS_NAME_MAX_LENGTH = 253
DNS_LABEL_PATTERN = re.compile(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$')

# Kubernetes name constraints
K8S_NAME_PATTERN = re.compile(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$')

# Reserved namespaces that cannot be used for user namespaces
RESERVED_NAMESPACES: Set[str] = {
    'kube-system',
    'kube-public',
    'kube-node-lease',
    'default',
}

# Valid RBAC verbs
VALID_VERBS: Set[str] = {
    'get', 'list', 'watch', 'create', 'update', 'patch', 'delete',
    'deletecollection', 'use', 'bind', 'escalate', 'impersonate', '*',
}


def validate_dns_label(value: str, field_name: str = "name") -> str:
    """Validate a DNS-1123 label (e.g., namespace name, service account name).

    Args:
        value: The string to validate
        field_name: Name of the field for error messages

    Returns:
        The validated string (lowercase)

    Raises:
        ValidationError: If validation fails
    """
    if not value:
        raise ValidationError(field_name, f"{field_name} cannot be empty")

    # Convert to lowercase for consistency
    value = value.lower()

    if len(value) > DNS_LABEL_MAX_LENGTH:
        raise ValidationError(
            field_name,
            f"{field_name} must be at most {DNS_LABEL_MAX_LENGTH} characters",
            value
        )

    if not DNS_LABEL_PATTERN.match(value):
        raise ValidationError(
            field_name,
            f"{field_name} must consist of lowercase alphanumeric characters or '-', "
            f"start with an alphanumeric character, and end with an alphanumeric character",
            value
        )

    return value


def validate_kubernetes_name(value: str, field_name: str = "name") -> str:
    """Validate a Kubernetes resource name.

    Args:
        value: The string to validate
        field_name: Name of the field for error messages

    Returns:
        The validated string (lowercase)

    Raises:
        ValidationError: If validation fails
    """
    if not value:
        raise ValidationError(field_name, f"{field_name} cannot be empty")

    # Convert to lowercase for consistency
    value = value.lower()

    if len(value) > DNS_NAME_MAX_LENGTH:
        raise ValidationError(
            field_name,
            f"{field_name} must be at most {DNS_NAME_MAX_LENGTH} characters",
            value
        )

    if not K8S_NAME_PATTERN.match(value):
        raise ValidationError(
            field_name,
            f"{field_name} must consist of lowercase alphanumeric characters, '-' or '.', "
            f"and must start and end with an alphanumeric character",
            value
        )

    return value


def validate_namespace(namespace: str, allow_reserved: bool = False) -> str:
    """Validate a namespace name.

    Args:
        namespace: The namespace to validate
        allow_reserved: Whether to allow reserved namespaces

    Returns:
        The validated namespace name

    Raises:
        ValidationError: If validation fails
    """
    namespace = validate_dns_label(namespace, "namespace")

    if not allow_reserved and namespace in RESERVED_NAMESPACES:
        raise ValidationError(
            "namespace",
            f"Cannot use reserved namespace '{namespace}'",
            namespace
        )

    return namespace


def validate_user_name(name: str) -> str:
    """Validate a user name for the User CRD.

    Args:
        name: The user name to validate

    Returns:
        The validated user name

    Raises:
        ValidationError: If validation fails
    """
    return validate_dns_label(name, "user_name")


def validate_group_name(name: str) -> str:
    """Validate a group name for the Group CRD.

    Args:
        name: The group name to validate

    Returns:
        The validated group name

    Raises:
        ValidationError: If validation fails
    """
    return validate_dns_label(name, "group_name")


def validate_role_name(name: str) -> str:
    """Validate a role name.

    Args:
        name: The role name to validate

    Returns:
        The validated role name

    Raises:
        ValidationError: If validation fails
    """
    return validate_kubernetes_name(name, "role_name")


def validate_cluster_role_reference(cluster_role: str, namespace: Optional[str] = None) -> dict:
    """Validate a cluster role reference in CRoles spec.

    Args:
        cluster_role: The cluster role name
        namespace: Optional namespace for the binding

    Returns:
        Validated cluster role reference dict

    Raises:
        ValidationError: If validation fails
    """
    result = {
        "clusterRole": validate_role_name(cluster_role)
    }

    if namespace:
        result["namespace"] = validate_namespace(namespace, allow_reserved=True)

    return result


def validate_croles_spec(croles: List[dict]) -> List[dict]:
    """Validate the CRoles spec from a User or Group CRD.

    Args:
        croles: List of cluster role assignments

    Returns:
        Validated list of cluster role assignments

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(croles, list):
        raise ValidationError("CRoles", "CRoles must be a list")

    validated = []
    seen_bindings: Set[tuple] = set()

    for i, crole in enumerate(croles):
        if not isinstance(crole, dict):
            raise ValidationError(
                f"CRoles[{i}]",
                "Each CRole entry must be an object"
            )

        cluster_role = crole.get("clusterRole")
        if not cluster_role:
            raise ValidationError(
                f"CRoles[{i}].clusterRole",
                "clusterRole is required"
            )

        namespace = crole.get("namespace")
        group = crole.get("group")

        entry = validate_cluster_role_reference(cluster_role, namespace)

        # Check for duplicates
        binding_key = (entry.get("namespace", ""), entry["clusterRole"])
        if binding_key in seen_bindings:
            raise ValidationError(
                f"CRoles[{i}]",
                f"Duplicate cluster role binding: {cluster_role} in namespace {namespace or 'cluster-wide'}"
            )
        seen_bindings.add(binding_key)

        if group:
            entry["group"] = validate_group_name(group)

        validated.append(entry)

    return validated


def validate_roles_spec(roles: List[str]) -> List[str]:
    """Validate the Roles spec from a User or Group CRD.

    Args:
        roles: List of role names

    Returns:
        Validated list of role names

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(roles, list):
        raise ValidationError("Roles", "Roles must be a list")

    validated = []
    seen_roles: Set[str] = set()

    for i, role in enumerate(roles):
        if not isinstance(role, str):
            raise ValidationError(
                f"Roles[{i}]",
                "Each role must be a string"
            )

        validated_role = validate_role_name(role)

        if validated_role in seen_roles:
            raise ValidationError(
                f"Roles[{i}]",
                f"Duplicate role: {role}"
            )
        seen_roles.add(validated_role)

        validated.append(validated_role)

    return validated


def validate_rbac_rule(rule: dict, index: int = 0) -> dict:
    """Validate an RBAC policy rule.

    Args:
        rule: The rule dict to validate
        index: Index for error messages

    Returns:
        Validated rule dict

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(rule, dict):
        raise ValidationError(f"rules[{index}]", "Rule must be an object")

    validated = {}

    # Validate apiGroups
    api_groups = rule.get("apiGroups", [])
    if not isinstance(api_groups, list):
        raise ValidationError(f"rules[{index}].apiGroups", "apiGroups must be a list")
    validated["apiGroups"] = api_groups

    # Validate resources
    resources = rule.get("resources", [])
    if not isinstance(resources, list):
        raise ValidationError(f"rules[{index}].resources", "resources must be a list")
    if not resources:
        raise ValidationError(f"rules[{index}].resources", "resources cannot be empty")
    validated["resources"] = resources

    # Validate verbs
    verbs = rule.get("verbs", [])
    if not isinstance(verbs, list):
        raise ValidationError(f"rules[{index}].verbs", "verbs must be a list")
    if not verbs:
        raise ValidationError(f"rules[{index}].verbs", "verbs cannot be empty")

    for verb in verbs:
        if verb not in VALID_VERBS:
            raise ValidationError(
                f"rules[{index}].verbs",
                f"Invalid verb: {verb}. Valid verbs are: {', '.join(sorted(VALID_VERBS))}"
            )
    validated["verbs"] = verbs

    # Optional: resourceNames
    resource_names = rule.get("resourceNames")
    if resource_names is not None:
        if not isinstance(resource_names, list):
            raise ValidationError(f"rules[{index}].resourceNames", "resourceNames must be a list")
        validated["resourceNames"] = resource_names

    return validated


def validate_role_spec(spec: dict) -> dict:
    """Validate a Role/ClusterRole spec.

    Args:
        spec: The spec dict to validate

    Returns:
        Validated spec dict

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(spec, dict):
        raise ValidationError("spec", "spec must be an object")

    rules = spec.get("rules", [])
    if not isinstance(rules, list):
        raise ValidationError("rules", "rules must be a list")

    validated_rules = []
    for i, rule in enumerate(rules):
        validated_rules.append(validate_rbac_rule(rule, i))

    return {"rules": validated_rules}


def validate_user_spec(spec: dict) -> dict:
    """Validate a complete User CRD spec.

    Args:
        spec: The spec dict to validate

    Returns:
        Validated spec dict

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(spec, dict):
        raise ValidationError("spec", "spec must be an object")

    validated = {}

    # Validate enabled flag
    enabled = spec.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValidationError("enabled", "enabled must be a boolean")
    validated["enabled"] = enabled

    # Validate CRoles
    croles = spec.get("CRoles", [])
    validated["CRoles"] = validate_croles_spec(croles)

    # Validate Roles
    roles = spec.get("Roles", [])
    validated["Roles"] = validate_roles_spec(roles)

    return validated


def validate_group_spec(spec: dict) -> dict:
    """Validate a complete Group CRD spec.

    Args:
        spec: The spec dict to validate

    Returns:
        Validated spec dict

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(spec, dict):
        raise ValidationError("spec", "spec must be an object")

    validated = {}

    # Validate CRoles
    croles = spec.get("CRoles", [])
    validated["CRoles"] = validate_croles_spec(croles)

    # Validate Roles
    roles = spec.get("Roles", [])
    validated["Roles"] = validate_roles_spec(roles)

    return validated
