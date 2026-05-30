from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required

from ..services.badges import record_badge_progress

games_bp = Blueprint("games", __name__, url_prefix="/games")


@games_bp.route("/")
def games_hub():
    return render_template("games/hub.html")


@games_bp.route("/memory")
def memory():
    return render_template("games/memory.html")


@games_bp.route("/coloring")
def coloring():
    return render_template("games/coloring.html")


@games_bp.route("/played", methods=["POST"])
@login_required
def played():
    """Tiny endpoint games hit once on a win to award the game-player badge."""
    record_badge_progress(current_user, "game-player")
    return jsonify(ok=True)
