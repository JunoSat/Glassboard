import os
from flask import Flask
from app.db import init_pool, execute_schema_file
from app.auth import auth_bp


def create_app():
    """Application Factory pattern to initialize Flask core layers."""
    app = Flask(__name__)

    # Initialize the database structures on startup
    init_pool()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(base_dir, 'app', 'schema.sql')
    execute_schema_file(schema_path)

    # Register our API route blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    return app


if __name__ == "__main__":
    app = create_app()
    print("Glassboard Server online at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)