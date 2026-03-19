import random
from collections import defaultdict
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from sqlalchemy import func

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


@battle_bp.route("/leaderboard")
def leaderboard():
    """Show all matchup vote tallies and the overall strongest hero ranking."""
    all_votes = BattleVote.query.all()

    # Tally total wins per hero
    total_wins = defaultdict(int)
    total_battles = defaultdict(int)  # total times appeared in a matchup

    # Collect per-matchup stats
    # Key: frozenset of (hero1_id, hero2_id) → {hero_id: wins}
    matchup_stats = {}
    for vote in all_votes:
        key = frozenset([vote.hero1_id, vote.hero2_id])
        if key not in matchup_stats:
            matchup_stats[key] = defaultdict(int)
        matchup_stats[key][vote.winner_id] += 1
        total_wins[vote.winner_id] += 1
        total_battles[vote.hero1_id] += 1
        total_battles[vote.hero2_id] += 1

    # Load all characters for lookup
    characters = {c.id: c for c in Character.query.all()}

    # Build matchup rows sorted by total votes descending
    matchup_rows = []
    for key, counts in matchup_stats.items():
        ids = list(key)
        if len(ids) < 2:
            continue
        h1_id, h2_id = ids[0], ids[1]
        h1 = characters.get(h1_id)
        h2 = characters.get(h2_id)
        if not h1 or not h2:
            continue
        h1_votes = counts.get(h1_id, 0)
        h2_votes = counts.get(h2_id, 0)
        total = h1_votes + h2_votes
        matchup_rows.append({
            "hero1": h1,
            "hero2": h2,
            "hero1_votes": h1_votes,
            "hero2_votes": h2_votes,
            "total_votes": total,
            "hero1_pct": round(h1_votes / total * 100) if total else 0,
            "hero2_pct": round(h2_votes / total * 100) if total else 0,
        })
    matchup_rows.sort(key=lambda r: r["total_votes"], reverse=True)

    # Build hero leaderboard: ranked by total wins
    hero_rankings = []
    for hero_id, hero in characters.items():
        wins = total_wins.get(hero_id, 0)
        battles = total_battles.get(hero_id, 0)
        # deduplicate battle counts (each vote records both hero1 & hero2)
        unique_battles = battles // 2 if battles > 0 else 0
        hero_rankings.append({
            "hero": hero,
            "wins": wins,
            "battles": unique_battles,
            "win_rate": round(wins / unique_battles * 100) if unique_battles else 0,
        })
    hero_rankings.sort(key=lambda r: (r["wins"], r["win_rate"]), reverse=True)

    total_votes_cast = len(all_votes)

    return render_template(
        "battle/leaderboard.html",
        matchup_rows=matchup_rows,
        hero_rankings=hero_rankings,
        total_votes_cast=total_votes_cast,
    )
