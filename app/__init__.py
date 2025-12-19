from flask import Flask
from config import Config
from .extensions import db, login_manager, migrate

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    # Register blueprints (controllers)
    from .views.auth_routes import auth_bp
    from .views.main_routes import main_bp
    from .views.comics_routes import comics_bp
    from .views.admin_routes import admin_bp
    from .views.characters_routes import characters_bp

    app.register_blueprint(characters_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(comics_bp, url_prefix="/comics")

    return app
