"""Metrics collector for k8s-iam-operator.

This module provides a background collector that periodically counts
User, Group, and Role CRDs and updates the Prometheus gauges.
"""

import logging
import threading
import time
from collections import defaultdict

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from app.config import Config
from app.api.metrics import (
    set_users_total,
    set_groups_total,
    set_roles_total,
    set_operator_info,
)
from app.version import __version__

logger = logging.getLogger(__name__)

# Collection interval in seconds
COLLECTION_INTERVAL = 30


class MetricsCollector:
    """Collects metrics from Kubernetes CRDs and updates Prometheus gauges."""

    def __init__(self):
        """Initialize the metrics collector."""
        self._running = False
        self._thread = None
        self._custom_api = None

    def _init_kubernetes_client(self):
        """Initialize the Kubernetes client."""
        try:
            config.load_incluster_config()
        except config.ConfigException:
            try:
                config.load_kube_config()
            except config.ConfigException:
                logger.warning("Could not load Kubernetes config")
                return False
        self._custom_api = client.CustomObjectsApi()
        return True

    def start(self):
        """Start the metrics collection background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Metrics collector started")

    def stop(self):
        """Stop the metrics collection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Metrics collector stopped")

    def _run(self):
        """Main collection loop."""
        # Set operator info metric
        set_operator_info(__version__)

        # Wait for Kubernetes client to be ready
        while self._running:
            if self._init_kubernetes_client():
                break
            logger.warning("Waiting for Kubernetes client...")
            time.sleep(5)

        # Collection loop
        while self._running:
            try:
                self._collect_metrics()
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")

            time.sleep(COLLECTION_INTERVAL)

    def _collect_metrics(self):
        """Collect all CRD metrics."""
        self._collect_user_metrics()
        self._collect_group_metrics()
        self._collect_role_metrics()

    def _collect_user_metrics(self):
        """Collect User CRD metrics."""
        try:
            users = self._custom_api.list_cluster_custom_object(
                group=Config.GROUP,
                version=Config.VERSION,
                plural=Config.PLURAL,
            )

            # Count users by namespace and type
            counts = defaultdict(lambda: {"human": 0, "serviceAccount": 0})

            for user in users.get("items", []):
                namespace = user.get("metadata", {}).get("namespace", "default")
                spec = user.get("spec", {})
                user_type = spec.get("userType", "serviceAccount")
                # Normalize type
                if user_type in ("human", "Human"):
                    counts[namespace]["human"] += 1
                else:
                    counts[namespace]["serviceAccount"] += 1

            # Update gauges
            for namespace, type_counts in counts.items():
                set_users_total(namespace, "human", type_counts["human"])
                set_users_total(namespace, "serviceAccount", type_counts["serviceAccount"])

            # Log total
            total_human = sum(c["human"] for c in counts.values())
            total_sa = sum(c["serviceAccount"] for c in counts.values())
            logger.debug(f"Collected user metrics: {total_human} human, {total_sa} serviceAccount")

        except ApiException as e:
            if e.status == 404:
                logger.debug("User CRD not found (not installed)")
            else:
                logger.error(f"Error listing users: {e.reason}")

    def _collect_group_metrics(self):
        """Collect Group CRD metrics."""
        try:
            groups = self._custom_api.list_cluster_custom_object(
                group=Config.GROUP,
                version=Config.VERSION,
                plural=Config.GPLURAL,
            )

            # Count groups by namespace
            counts = defaultdict(int)

            for group in groups.get("items", []):
                namespace = group.get("metadata", {}).get("namespace", "default")
                counts[namespace] += 1

            # Update gauges
            for namespace, count in counts.items():
                set_groups_total(namespace, count)

            total = sum(counts.values())
            logger.debug(f"Collected group metrics: {total} groups")

        except ApiException as e:
            if e.status == 404:
                logger.debug("Group CRD not found (not installed)")
            else:
                logger.error(f"Error listing groups: {e.reason}")

    def _collect_role_metrics(self):
        """Collect Role and ClusterRole CRD metrics."""
        total_roles = 0
        total_cluster_roles = 0

        # Collect namespaced Roles
        try:
            roles = self._custom_api.list_cluster_custom_object(
                group=Config.GROUP,
                version=Config.VERSION,
                plural=Config.RPLURAL,
            )

            # Count roles by namespace
            role_counts = defaultdict(int)

            for role in roles.get("items", []):
                namespace = role.get("metadata", {}).get("namespace", "default")
                role_counts[namespace] += 1

            # Update gauges
            for namespace, count in role_counts.items():
                set_roles_total(namespace, "Role", count)

            total_roles = sum(role_counts.values())

        except ApiException as e:
            if e.status == 404:
                logger.debug("Role CRD not found (not installed)")
            else:
                logger.error(f"Error listing roles: {e.reason}")

        # Collect ClusterRoles
        try:
            cluster_roles = self._custom_api.list_cluster_custom_object(
                group=Config.GROUP,
                version=Config.VERSION,
                plural=Config.CRPLURAL,
            )

            total_cluster_roles = len(cluster_roles.get("items", []))
            set_roles_total("cluster", "ClusterRole", total_cluster_roles)

        except ApiException as e:
            if e.status == 404:
                logger.debug("ClusterRole CRD not found (not installed)")
            else:
                logger.error(f"Error listing cluster roles: {e.reason}")

        logger.debug(
            f"Collected role metrics: {total_roles} roles, "
            f"{total_cluster_roles} cluster roles"
        )


# Global collector instance
_collector = None


def start_metrics_collector():
    """Start the global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    _collector.start()


def stop_metrics_collector():
    """Stop the global metrics collector."""
    global _collector
    if _collector:
        _collector.stop()
