"""Flask API for health checks and metrics.

This module provides the Flask application factory and route registration.
"""

from flask import Flask
import logging

from app.api.health import health_bp
from app.api.metrics import metrics_bp
from app.utils.no200filter import No200Filter

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Configured Flask application
    """
    app = Flask(__name__)

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(metrics_bp)

    # Add logging filter to suppress 200 OK spam
    if not app.debug:
        no200_filter = No200Filter()
        for handler in logging.getLogger('werkzeug').handlers:
            handler.addFilter(no200_filter)

    logger.info("Flask application initialized")
    return app
