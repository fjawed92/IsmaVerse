from flask import Blueprint, render_template
from flask_login import current_user

from ..services.badges import get_user_badge_states, record_badge_progress

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def home():
    badge_states = {}
    if current_user.is_authenticated:
        record_badge_progress(current_user, "secret-visitor")
        badge_states = get_user_badge_states(current_user)
    return render_template("main/home.html", badge_states=badge_states)
