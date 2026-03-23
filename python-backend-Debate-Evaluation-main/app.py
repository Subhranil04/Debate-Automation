from flask import Flask
from config import Config
from api.routes import api_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register the API blueprint
    app.register_blueprint(api_bp, url_prefix="/api")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True if Config.FLASK_ENV == "development" else False)