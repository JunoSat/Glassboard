from flask import Flask
from flask_jwt_extended import JWTManager
from app.config import Config
from app.models import db, User
from app.listeners import register_listeners

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    
    jwt = JWTManager(app)
    
    # Configure JWT User Lookup
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.filter_by(id=int(identity)).one_or_none()

    # Register SQLAlchemy event listeners
    register_listeners()

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.modules import modules_bp
    from app.routes.handshakes import handshakes_bp
    from app.routes.audit import audit_bp

    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(modules_bp, url_prefix='/api')
    app.register_blueprint(handshakes_bp, url_prefix='/api')
    app.register_blueprint(audit_bp, url_prefix='/api')

    return app
