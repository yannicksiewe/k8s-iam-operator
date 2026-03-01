"""Health check endpoints for k8s-iam-operator.

This module provides health check endpoints for Kubernetes liveness
and readiness probes.
"""

from flask import Blueprint, jsonify
from typing import Tuple, Dict, Any

health_bp = Blueprint('health', __name__)


@health_bp.route('/actuator/health', methods=['GET'])
def health() -> Tuple[Dict[str, Any], int]:
    """Health check endpoint for Kubernetes probes.

    Returns:
        JSON response with health status
    """
    return jsonify(status="UP"), 200


@health_bp.route('/health', methods=['GET'])
def health_short() -> Tuple[Dict[str, Any], int]:
    """Shortened health check endpoint.

    Returns:
        JSON response with health status
    """
    return jsonify(status="UP"), 200


@health_bp.route('/ready', methods=['GET'])
def ready() -> Tuple[Dict[str, Any], int]:
    """Readiness check endpoint.

    Returns:
        JSON response with readiness status
    """
    # In the future, this could check:
    # - Kubernetes API connectivity
    # - Required CRDs are installed
    # - etc.
    return jsonify(status="ready"), 200


@health_bp.route('/live', methods=['GET'])
def live() -> Tuple[Dict[str, Any], int]:
    """Liveness check endpoint.

    Returns:
        JSON response with liveness status
    """
    return jsonify(status="alive"), 200
