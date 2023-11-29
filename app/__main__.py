import threading
import warnings
from app.kopf_handlers import main as kopf_main
from app.flask_app import app

# Suppress specific FutureWarnings
warnings.filterwarnings("ignore", category=FutureWarning)


def run_flask_app():
    app.run(host='0.0.0.0', port=8081, use_reloader=False, threaded=True, debug=False)


if __name__ == "__main__":
    # Start Kopf in a separate thread
    kopf_thread = threading.Thread(target=kopf_main)
    kopf_thread.start()

    # Start Flask app in the main thread
    run_flask_app()
