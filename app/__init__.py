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
    from .views.villain_routes import villains_bp
    from .views.battle_routes import battle_bp
    from .views.team_routes import team_bp
    from .views.extras_routes import extras_bp
    from .views.universe_routes import universe_bp
    from .views.profile_routes import profile_bp
    from .views.games_routes import games_bp

    app.register_blueprint(characters_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(comics_bp, url_prefix="/comics")
    app.register_blueprint(villains_bp)
    app.register_blueprint(battle_bp)
    app.register_blueprint(team_bp)
    app.register_blueprint(extras_bp)
    app.register_blueprint(universe_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(games_bp)

    # Add enumerate as a Jinja2 global
    app.jinja_env.globals["enumerate"] = enumerate

    # Expose the current user's favorites + theme pref to every template so
    # the shared partials can render the right state without each route
    # having to pass it explicitly.
    @app.context_processor
    def inject_user_extras():
        from flask_login import current_user
        fav_keys = set()
        avatar_emoji = None
        if current_user.is_authenticated:
            try:
                from .services.profiles import get_favorite_keys, AVATAR_EMOJI
                fav_keys = get_favorite_keys(current_user)
                if current_user.profile and current_user.profile.avatar:
                    avatar_emoji = AVATAR_EMOJI.get(current_user.profile.avatar)
            except Exception:
                fav_keys = set()
        return {
            "fav_keys": fav_keys,
            "fav_source": "server" if current_user.is_authenticated else "local",
            "user_avatar_emoji": avatar_emoji,
        }

    return app
