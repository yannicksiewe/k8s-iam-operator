"""Main entry point for k8s-iam-operator.

This module starts the Kopf operator and Flask health/metrics server.
"""

import threading
import warnings
import logging

from app.kopf_handlers import main as kopf_main
from app.api import create_app
from app.config import get_config

# Suppress specific FutureWarnings from dependencies
warnings.filterwarnings("ignore", category=FutureWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def run_flask_app():
    """Start the Flask health/metrics server."""
    config = get_config()
    app = create_app()

    logger.info("Starting Flask health/metrics server on port 8081")
    app.run(
        host='0.0.0.0',
        port=8081,
        use_reloader=False,
        threaded=True,
        debug=False
    )


if __name__ == "__main__":
    logger.info("Starting k8s-iam-operator")

    # Start Kopf in a separate thread
    kopf_thread = threading.Thread(target=kopf_main, daemon=True)
    kopf_thread.start()

    # Start Flask app in the main thread
    run_flask_app()
