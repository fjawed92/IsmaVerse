from flask import Flask
from config import Config
from .extensions import db, migrate

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints (controllers)
    from .views.main_routes import main_bp
    from .views.comics_routes import comics_bp
    from .views.admin_routes import admin_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(comics_bp, url_prefix="/comics")

    return app
