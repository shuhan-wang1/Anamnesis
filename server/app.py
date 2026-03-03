"""Flask application entry point."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, send_from_directory
from flask_cors import CORS
from config import FRONTEND_DIR, DATA_DIR
import server.state as state

app = Flask(__name__, static_folder=None)
CORS(app)


# --- Static file serving ---

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)


# --- Register API blueprints ---

from server.routes.graph_api import graph_bp
from server.routes.progress_api import progress_bp
from server.routes.diagnostic_api import diagnostic_bp
from server.routes.learning_api import learning_bp
from server.routes.quiz_api import quiz_bp
from server.routes.dashboard_api import dashboard_bp
from server.routes.spaced_repetition import sr_bp
from server.routes.course_api import course_bp

app.register_blueprint(graph_bp, url_prefix='/api')
app.register_blueprint(progress_bp, url_prefix='/api')
app.register_blueprint(diagnostic_bp, url_prefix='/api')
app.register_blueprint(learning_bp, url_prefix='/api')
app.register_blueprint(quiz_bp, url_prefix='/api')
app.register_blueprint(dashboard_bp, url_prefix='/api')
app.register_blueprint(sr_bp, url_prefix='/api')
app.register_blueprint(course_bp, url_prefix='/api')


def main():
    state.init(DATA_DIR)
    print("Starting Anamnesis at http://localhost:5000")
    app.run(host='127.0.0.1', port=5000, debug=False)


if __name__ == '__main__':
    main()
