from flask import (
    Blueprint, flash, jsonify, redirect, render_template, request, url_for
)
from flask_login import current_user, login_required

from ..services.profiles import (
    AVATARS, VALID_ITEM_TYPES, get_or_create_profile, get_favorites,
    get_favorite_keys, toggle_favorite,
)
from ..services.streaks import record_streak_ping, get_streak
from ..services.badges import (
    get_badge_meta, get_user_badge_states, record_badge_progress,
)

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/collection")
def collection():
    """My Stuff — favorites, badges and avatar.

    Logged-in users get server data; anonymous kids get a localStorage
    view rendered by main.js (same markup, data-fav-source="local").
    """
    badge_meta = get_badge_meta()

    if current_user.is_authenticated:
        profile = get_or_create_profile(current_user)
        favorites = get_favorites(current_user)
        badge_states = get_user_badge_states(current_user)
        streak = get_streak(current_user)
        source = "server"
    else:
        profile = None
        favorites = {"heroes": [], "villains": [], "comics": []}
        badge_states = {}
        streak = {"current": 0, "longest": 0, "total": 0}
        source = "local"

    return render_template(
        "profile/collection.html",
        profile=profile,
        favorites=favorites,
        badge_meta=badge_meta,
        badge_states=badge_states,
        streak=streak,
        avatars=AVATARS,
        fav_source=source,
    )


@profile_bp.route("/collection/profile", methods=["GET", "POST"])
@login_required
def profile_edit():
    profile = get_or_create_profile(current_user)

    if request.method == "POST":
        avatar = (request.form.get("avatar") or "").strip()
        display_name = (request.form.get("display_name") or "").strip()
        valid_slugs = {slug for slug, _, _ in AVATARS}
        profile.avatar = avatar if avatar in valid_slugs else None
        profile.display_name = display_name[:80] or None
        from ..extensions import db
        db.session.add(profile)
        db.session.commit()
        flash("Your hero profile is saved!", "success")
        return redirect(url_for("profile.collection"))

    return render_template(
        "profile/profile_edit.html", profile=profile, avatars=AVATARS
    )


@profile_bp.route("/favorites/toggle", methods=["POST"])
@login_required
def favorites_toggle():
    item_type = (request.form.get("item_type") or "").strip()
    try:
        item_id = int(request.form.get("item_id", ""))
    except (TypeError, ValueError):
        item_id = 0

    if item_type not in VALID_ITEM_TYPES or item_id <= 0:
        msg = "That can't be favorited."
        if _wants_json():
            return jsonify(ok=False, error=msg), 400
        flash(msg, "danger")
        return redirect(request.form.get("next") or url_for("profile.collection"))

    favorited = toggle_favorite(current_user, item_type, item_id)
    if favorited:
        record_badge_progress(current_user, "collector")

    if _wants_json():
        return jsonify(ok=True, favorited=favorited)

    return redirect(request.form.get("next") or url_for("profile.collection"))


@profile_bp.route("/streak/ping", methods=["POST"])
@login_required
def streak_ping():
    result = record_streak_ping(current_user)
    return jsonify(ok=True, **result)


def _wants_json() -> bool:
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in (request.headers.get("Accept") or "")
    )
