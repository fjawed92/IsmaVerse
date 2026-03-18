import random
from datetime import date

from flask import Blueprint, render_template
from flask_login import current_user

from ..models.character import Character
from ..services.badges import get_user_badge_states, record_badge_progress, get_badge_meta

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    badge_states = {}
    if current_user.is_authenticated:
        record_badge_progress(current_user, "secret-visitor")
        record_badge_progress(current_user, "true-fan")
        badge_states = get_user_badge_states(current_user)

    # Hero spotlight: pick a consistent daily hero using today's date
    characters = Character.query.all()
    spotlight = None
    if characters:
        day_index = date.today().timetuple().tm_yday
        spotlight = characters[day_index % len(characters)]

    badge_meta = get_badge_meta()

    return render_template(
        "main/home.html",
        badge_states=badge_states,
        badge_meta=badge_meta,
        spotlight=spotlight,
        all_badges=list(badge_meta.keys()),
    )
