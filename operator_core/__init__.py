import kopf
import threading
import warnings
import os
from flask import Flask, jsonify, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from .handlers import create_group_handler, create_role_handler, create_user_handler
from .controllers import update_group_handler, update_user_handler
from .controllers import delete_group_handler, delete_role_handler, delete_user_handler

GROUP = os.environ.get('GROUP_NAME', 'k8sio.auth')
VERSION = os.environ.get('VERSION', 'v1')
PLURAL = os.environ.get('PLURAL', 'users')
GPLURAL = os.environ.get('GROUP_PLURAL', 'groups')
RPLURAL = os.environ.get('ROLE_PLURAL', 'roles')
CRPLURAL = os.environ.get('CLUSTER_ROLE_PLURAL', 'clusterroles')

# Metrics
app = Flask(__name__)


# Check if the dashboard should be enabled
if os.environ.get('ENABLE_DASHBOARD', 'False') == 'True':
    import flask_monitoringdashboard as dashboard
    dashboard.bind(app)


# if tracing is enabled, setup the tracer
if os.environ.get('ENABLE_TRACING', 'False') == 'True':
    from configs.tracing import setup_tracer
    tracer = setup_tracer()

# Suppress specific FutureWarnings
warnings.filterwarnings("ignore", category=FutureWarning)


# define the Kopf operator
@kopf.on.create(GROUP, VERSION, GPLURAL)
def create_group_fn(body, spec, **kwargs):
    create_group_handler(body, spec, **kwargs)


@kopf.on.update(GROUP, VERSION, GPLURAL)
def update_group_fn(body, spec, **kwargs):
    update_group_handler(body, spec, **kwargs)


@kopf.on.delete(GROUP, VERSION, GPLURAL)
def delete_group_fn(body, **kwargs):
    delete_group_handler(body, **kwargs)


@kopf.on.create(GROUP, VERSION, RPLURAL)
@kopf.on.create(GROUP, VERSION, CRPLURAL)
@kopf.on.update(GROUP, VERSION, RPLURAL)
@kopf.on.update(GROUP, VERSION, CRPLURAL)
def create_role_fn(spec, **kwargs):
    create_role_handler(spec, **kwargs)


@kopf.on.delete(GROUP, VERSION, RPLURAL)
@kopf.on.delete(GROUP, VERSION, CRPLURAL)
def delete_role_fn(**kwargs):
    delete_role_handler(**kwargs)


@kopf.on.create(GROUP, VERSION, PLURAL)
def create_user_fn(body, spec, **kwargs):
    create_user_handler(body, spec, **kwargs)


@kopf.on.update(GROUP, VERSION, PLURAL)
def update_user_fn(body, spec, **kwargs):
    update_user_handler(body, spec, **kwargs)


@kopf.on.delete(GROUP, VERSION, PLURAL)
def delete_user_fn(body, spec, **kwargs):
    delete_user_handler(body, spec, **kwargs)


# enable status endpoint
@app.route('/actuator/health', methods=['GET'])
def health():
    # Add your actuator logic here
    return jsonify(status="UP"), 200


# enable endpoint for prometheus operator
@app.route('/actuator/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


def run_flask_app():
    app.run(host='0.0.0.0', port=8080, use_reloader=False, threaded=True, debug=True)


# start the operator
def main():
    # Start Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    # Start Kopf
    kopf.run()


if __name__ == '__main__':
    main()
