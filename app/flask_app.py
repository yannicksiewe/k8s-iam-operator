from flask import Flask, jsonify, Response
from app.utils.no200filter import No200Filter  # Adjust this import based on your project structure
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# Add the No200Filter to Flask's logger
if not app.debug:
    no200_filter = No200Filter()
    for handler in app.logger.handlers:
        handler.addFilter(no200_filter)


def register_routes(app):
    @app.route('/actuator/health', methods=['GET'])
    def health():
        return jsonify(status="UP"), 200

    @app.route('/actuator/metrics')
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


register_routes(app)

if __name__ == '__main__':
    app.run(debug=False)  # Set debug=False for production
