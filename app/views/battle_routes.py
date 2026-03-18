import random
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from ..extensions import db
from ..models.character import Character
from ..models.battle import BattleVote
from ..services.badges import record_badge_progress

battle_bp = Blueprint("battle", __name__, url_prefix="/battle")


def _get_session_key() -> str:
    if "battle_session" not in session:
        import uuid
        session["battle_session"] = uuid.uuid4().hex
    return session["battle_session"]


@battle_bp.route("/")
def arena():
    characters = Character.query.all()
    if len(characters) < 2:
        return render_template("battle/arena.html", hero1=None, hero2=None, characters=characters)

    hero1_id = request.args.get("hero1", type=int)
    hero2_id = request.args.get("hero2", type=int)

    if hero1_id and hero2_id and hero1_id != hero2_id:
        hero1 = Character.query.get(hero1_id)
        hero2 = Character.query.get(hero2_id)
    else:
        picks = random.sample(characters, 2)
        hero1, hero2 = picks[0], picks[1]

    # Build vote counts for this matchup (both orderings)
    all_votes = BattleVote.query.filter(
        (
            (BattleVote.hero1_id == hero1.id) & (BattleVote.hero2_id == hero2.id)
        ) | (
            (BattleVote.hero1_id == hero2.id) & (BattleVote.hero2_id == hero1.id)
        )
    ).all()

    vote_counts = {hero1.id: 0, hero2.id: 0}
    for v in all_votes:
        if v.winner_id in vote_counts:
            vote_counts[v.winner_id] += 1

    total_votes = sum(vote_counts.values())
    hero1_pct = round(vote_counts[hero1.id] / total_votes * 100) if total_votes else 0
    hero2_pct = 100 - hero1_pct if total_votes else 0

    return render_template(
        "battle/arena.html",
        hero1=hero1,
        hero2=hero2,
        characters=characters,
        vote_counts=vote_counts,
        total_votes=total_votes,
        hero1_pct=hero1_pct,
        hero2_pct=hero2_pct,
    )


@battle_bp.route("/vote", methods=["POST"])
def vote():
    hero1_id = request.form.get("hero1_id", type=int)
    hero2_id = request.form.get("hero2_id", type=int)
    winner_id = request.form.get("winner_id", type=int)

    if not hero1_id or not hero2_id or not winner_id:
        flash("Invalid vote.", "danger")
        return redirect(url_for("battle.arena"))

    if winner_id not in (hero1_id, hero2_id):
        flash("Invalid vote selection.", "danger")
        return redirect(url_for("battle.arena"))

    session_key = _get_session_key()

    # Prevent double-voting same matchup (check both orderings)
    existing = BattleVote.query.filter(
        BattleVote.session_key == session_key,
        (
            (BattleVote.hero1_id == hero1_id) & (BattleVote.hero2_id == hero2_id)
        ) | (
            (BattleVote.hero1_id == hero2_id) & (BattleVote.hero2_id == hero1_id)
        )
    ).first()

    if existing:
        flash("You already voted in this battle! Try a new matchup.", "info")
        return redirect(url_for("battle.arena", hero1=hero1_id, hero2=hero2_id))

    vote = BattleVote(
        hero1_id=hero1_id,
        hero2_id=hero2_id,
        winner_id=winner_id,
        session_key=session_key,
        user_id=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(vote)
    db.session.commit()

    if current_user.is_authenticated:
        record_badge_progress(current_user, "battle-voter")

    flash("Vote cast! The arena roars!", "success")
    return redirect(url_for("battle.arena", hero1=hero1_id, hero2=hero2_id))
