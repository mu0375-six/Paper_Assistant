from flask import Flask

from .main import register_routes


def create_app():
    app = Flask(__name__, static_folder="../web", static_url_path="/static")
    register_routes(app)
    return app
