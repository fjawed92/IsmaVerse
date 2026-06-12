from flask import (
    Blueprint, flash, jsonify, redirect, render_template, request, url_for
)
from flask_login import current_user, login_required

from ..models.character import Character
from ..services.badges import record_badge_progress
from ..services.games import (
    GAME_SLUGS, claim_champion, get_champion_view, get_leaderboard,
    get_user_best, submit_score,
)

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


@games_bp.route("/poppi-jump")
def poppi_jump():
    best = get_user_best(current_user, "poppi-jump") if current_user.is_authenticated else 0
    return render_template("games/poppi_jump.html", best=best)


@games_bp.route("/spaceship")
def spaceship():
    best = get_user_best(current_user, "spaceship") if current_user.is_authenticated else 0
    return render_template("games/spaceship.html", best=best)


@games_bp.route("/whack-a-mole")
def whack_a_mole():
    best = get_user_best(current_user, "whack-a-mole") if current_user.is_authenticated else 0
    return render_template("games/whack_a_mole.html", best=best)


@games_bp.route("/snake")
def snake():
    best = get_user_best(current_user, "snake") if current_user.is_authenticated else 0
    return render_template("games/snake.html", best=best)


@games_bp.route("/simon-says")
def simon_says():
    best = get_user_best(current_user, "simon-says") if current_user.is_authenticated else 0
    return render_template("games/simon_says.html", best=best)


@games_bp.route("/brick-breaker")
def brick_breaker():
    best = get_user_best(current_user, "brick-breaker") if current_user.is_authenticated else 0
    return render_template("games/brick_breaker.html", best=best)


@games_bp.route("/played", methods=["POST"])
@login_required
def played():
    """Tiny endpoint games hit once on a win to award the game-player badge."""
    record_badge_progress(current_user, "game-player")
    return jsonify(ok=True)


@games_bp.route("/score", methods=["POST"])
@login_required
def score():
    """Arcade games POST their final score here on game over."""
    data = request.get_json(silent=True) or {}
    try:
        result = submit_score(current_user, data.get("game"), data.get("score"))
    except ValueError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    return jsonify(ok=True, **result)


@games_bp.route("/leaderboard")
def leaderboard():
    boards = {slug: get_leaderboard(slug) for slug in GAME_SLUGS}
    champion = None
    characters = []
    if current_user.is_authenticated:
        champion = get_champion_view(current_user)
        characters = Character.query.order_by(Character.superhero_name).all()
    return render_template(
        "games/leaderboard.html",
        game_names=GAME_SLUGS,
        boards=boards,
        champion=champion,
        characters=characters,
    )


@games_bp.route("/champion/claim", methods=["POST"])
@login_required
def champion_claim():
    try:
        claim_champion(current_user, request.form.get("character_id"))
    except ValueError as exc:
        if _wants_json():
            return jsonify(ok=False, error=str(exc)), 400
        flash(str(exc), "danger")
        return redirect(url_for("games.leaderboard"))

    if _wants_json():
        return jsonify(ok=True)
    flash("Your champion is claimed! 🦸", "success")
    return redirect(url_for("games.leaderboard"))


def _wants_json() -> bool:
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in (request.headers.get("Accept") or "")
    )
