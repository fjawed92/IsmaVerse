from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.character import Character
from ..models.team import HeroTeam
from ..services.badges import record_badge_progress

team_bp = Blueprint("teams", __name__, url_prefix="/teams")

TEAM_COLORS = ["blue", "red", "green", "yellow", "pink", "purple"]


@team_bp.route("/")
def list_teams():
    teams = HeroTeam.query.order_by(HeroTeam.created_at.desc()).all()
    return render_template("teams/list.html", teams=teams)


@team_bp.route("/create", methods=["GET", "POST"])
def create_team():
    characters = Character.query.order_by(Character.superhero_name).all()

    if request.method == "GET":
        return render_template("teams/create.html", characters=characters, colors=TEAM_COLORS)

    name = " ".join(request.form.get("name", "").split())
    slogan = " ".join(request.form.get("slogan", "").split())
    color = request.form.get("color", "blue")
    member_ids = request.form.getlist("members")

    if not name:
        flash("Team needs a name!", "danger")
        return redirect(url_for("teams.create_team"))

    if len(member_ids) < 2:
        flash("Pick at least 2 heroes for your team!", "danger")
        return redirect(url_for("teams.create_team"))

    if color not in TEAM_COLORS:
        color = "blue"

    members = Character.query.filter(Character.id.in_([int(m) for m in member_ids])).all()

    team = HeroTeam(
        name=name,
        slogan=slogan or None,
        color=color,
        created_by=current_user.id if current_user.is_authenticated else None,
    )
    team.members = members
    try:
        db.session.add(team)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Something went wrong saving your team. Please try again.", "danger")
        return redirect(url_for("teams.create_team"))

    if current_user.is_authenticated:
        record_badge_progress(current_user, "team-player")

    flash(f"Team '{name}' assembled! Time to save the world!", "success")
    return redirect(url_for("teams.team_detail", team_id=team.id))


@team_bp.route("/<int:team_id>")
def team_detail(team_id):
    team = HeroTeam.query.get_or_404(team_id)
    return render_template("teams/detail.html", team=team)
