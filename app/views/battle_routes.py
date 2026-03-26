import json
import random
from collections import defaultdict

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from ..extensions import db
from ..models.character import Character
from ..models.villain import Villain
from ..models.battle import BattleVote
from ..models.arena_battle import ArenaBattleVote, TeamBattle, TeamBattleVote
from ..services.badges import record_badge_progress
from ..services.comic_generator import generate_battle_narration, generate_team_battle_narration

battle_bp = Blueprint("battle", __name__, url_prefix="/battle")


# ─── Helpers ────────────────────────────────────────────────────────────────

def _get_session_key() -> str:
    if "battle_session" not in session:
        import uuid
        session["battle_session"] = uuid.uuid4().hex
    return session["battle_session"]


def _get_combatant(fighter_type: str, fighter_id: int) -> dict | None:
    """Return a unified combatant dict regardless of hero/villain type."""
    if fighter_type == "hero":
        c = Character.query.get(fighter_id)
        if not c:
            return None
        return {
            "type": "hero",
            "id": c.id,
            "name": c.superhero_name,
            "powers": c.powers or "???",
            "weakness": c.weakness or "Unknown",
            "power_level": c.power_level,
            "image_file": c.image_file,
            "image_folder": "characters",
            "color": "var(--comic-blue)",
            "bg_color": "#d0e8ff",
            "label": "⚡ HERO",
            "gender": c.gender or "male",
        }
    elif fighter_type == "villain":
        v = Villain.query.get(fighter_id)
        if not v:
            return None
        return {
            "type": "villain",
            "id": v.id,
            "name": v.villain_name,
            "powers": v.powers or "???",
            "weakness": v.weakness or "Unknown",
            "power_level": v.power_level,
            "image_file": v.image_file,
            "image_folder": "villains",
            "color": "var(--comic-red)",
            "bg_color": "#ffd0d0",
            "label": "😈 VILLAIN",
        }
    return None


def _parse_fighter_param(val: str) -> tuple[str, int] | tuple[None, None]:
    """Parse 'hero:3' or 'villain:7' → ('hero', 3)."""
    if not val or ":" not in val:
        return None, None
    parts = val.split(":", 1)
    try:
        return parts[0], int(parts[1])
    except (ValueError, IndexError):
        return None, None


def _all_combatants():
    """Return all heroes and villains as grouped lists."""
    heroes = Character.query.order_by(Character.superhero_name).all()
    villains = Villain.query.order_by(Villain.villain_name).all()
    return heroes, villains


# ─── 1v1 Arena ──────────────────────────────────────────────────────────────

@battle_bp.route("/")
def arena():
    heroes, villains = _all_combatants()
    all_combatants = (
        [{"type": "hero", "id": h.id, "name": h.superhero_name} for h in heroes]
        + [{"type": "villain", "id": v.id, "name": v.villain_name} for v in villains]
    )
    total_fighters = len(all_combatants)

    if total_fighters < 2:
        return render_template(
            "battle/arena.html",
            fighter1=None, fighter2=None,
            all_combatants=all_combatants,
            vote_counts={}, total_votes=0,
            fighter1_pct=0, fighter2_pct=0,
            narration=None,
        )

    # Parse fighter params e.g. ?f1=hero:1&f2=villain:3
    f1_raw = request.args.get("f1", "")
    f2_raw = request.args.get("f2", "")
    f1_type, f1_id = _parse_fighter_param(f1_raw)
    f2_type, f2_id = _parse_fighter_param(f2_raw)

    # Backward-compat: old ?hero1=&hero2= links
    if not f1_type:
        h1_id = request.args.get("hero1", type=int)
        if h1_id:
            f1_type, f1_id = "hero", h1_id
    if not f2_type:
        h2_id = request.args.get("hero2", type=int)
        if h2_id:
            f2_type, f2_id = "hero", h2_id

    fighter1 = _get_combatant(f1_type, f1_id) if f1_type else None
    fighter2 = _get_combatant(f2_type, f2_id) if f2_type else None

    if not fighter1 or not fighter2 or (fighter1["type"] == fighter2["type"] and fighter1["id"] == fighter2["id"]):
        # Pick two random combatants
        picks = random.sample(all_combatants, 2)
        fighter1 = _get_combatant(picks[0]["type"], picks[0]["id"])
        fighter2 = _get_combatant(picks[1]["type"], picks[1]["id"])

    # Vote counts from ArenaBattleVote
    all_votes = ArenaBattleVote.query.filter(
        db.or_(
            db.and_(
                ArenaBattleVote.fighter1_type == fighter1["type"],
                ArenaBattleVote.fighter1_id == fighter1["id"],
                ArenaBattleVote.fighter2_type == fighter2["type"],
                ArenaBattleVote.fighter2_id == fighter2["id"],
            ),
            db.and_(
                ArenaBattleVote.fighter1_type == fighter2["type"],
                ArenaBattleVote.fighter1_id == fighter2["id"],
                ArenaBattleVote.fighter2_type == fighter1["type"],
                ArenaBattleVote.fighter2_id == fighter1["id"],
            ),
        )
    ).all()

    f1_key = (fighter1["type"], fighter1["id"])
    f2_key = (fighter2["type"], fighter2["id"])
    vote_counts = {f1_key: 0, f2_key: 0}
    for v in all_votes:
        key = (v.winner_type, v.winner_id)
        if key in vote_counts:
            vote_counts[key] += 1

    total_votes = sum(vote_counts.values())
    f1_pct = round(vote_counts[f1_key] / total_votes * 100) if total_votes else 0
    f2_pct = 100 - f1_pct if total_votes else 0

    # Show narration from most recent vote if user just voted
    narration = None
    last_vote_id = request.args.get("voted", type=int)
    if last_vote_id:
        last_vote = ArenaBattleVote.query.get(last_vote_id)
        if last_vote:
            narration = last_vote.narration

    return render_template(
        "battle/arena.html",
        fighter1=fighter1,
        fighter2=fighter2,
        all_combatants=all_combatants,
        vote_counts=vote_counts,
        total_votes=total_votes,
        fighter1_pct=f1_pct,
        fighter2_pct=f2_pct,
        narration=narration,
        f1_key=f"{fighter1['type']}:{fighter1['id']}",
        f2_key=f"{fighter2['type']}:{fighter2['id']}",
    )


@battle_bp.route("/vote", methods=["POST"])
def vote():
    f1_type = request.form.get("f1_type", "")
    f1_id   = request.form.get("f1_id", type=int)
    f2_type = request.form.get("f2_type", "")
    f2_id   = request.form.get("f2_id", type=int)
    w_type  = request.form.get("winner_type", "")
    w_id    = request.form.get("winner_id", type=int)

    if not all([f1_type, f1_id, f2_type, f2_id, w_type, w_id]):
        flash("Invalid vote.", "danger")
        return redirect(url_for("battle.arena"))

    # winner must be one of the two fighters
    if not ((w_type == f1_type and w_id == f1_id) or (w_type == f2_type and w_id == f2_id)):
        flash("Invalid vote selection.", "danger")
        return redirect(url_for("battle.arena"))

    session_key = _get_session_key()

    # Prevent double-voting same matchup
    existing = ArenaBattleVote.query.filter(
        ArenaBattleVote.session_key == session_key,
        db.or_(
            db.and_(
                ArenaBattleVote.fighter1_type == f1_type,
                ArenaBattleVote.fighter1_id == f1_id,
                ArenaBattleVote.fighter2_type == f2_type,
                ArenaBattleVote.fighter2_id == f2_id,
            ),
            db.and_(
                ArenaBattleVote.fighter1_type == f2_type,
                ArenaBattleVote.fighter1_id == f2_id,
                ArenaBattleVote.fighter2_type == f1_type,
                ArenaBattleVote.fighter2_id == f1_id,
            ),
        )
    ).first()

    if existing:
        flash("You already voted in this battle! Try a new matchup.", "info")
        return redirect(url_for("battle.arena", f1=f"{f1_type}:{f1_id}", f2=f"{f2_type}:{f2_id}"))

    # Fetch combatant data for narration
    fighter1 = _get_combatant(f1_type, f1_id)
    fighter2 = _get_combatant(f2_type, f2_id)
    winner   = _get_combatant(w_type, w_id)

    narration = None
    if fighter1 and fighter2 and winner:
        try:
            narration = generate_battle_narration(
                fighter1["name"], fighter1["powers"],
                fighter2["name"], fighter2["powers"],
                winner["name"],
            )
        except Exception:
            pass  # narration is optional

    arena_vote = ArenaBattleVote(
        fighter1_type=f1_type, fighter1_id=f1_id,
        fighter2_type=f2_type, fighter2_id=f2_id,
        winner_type=w_type, winner_id=w_id,
        narration=narration,
        session_key=session_key,
        user_id=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(arena_vote)
    db.session.commit()

    if current_user.is_authenticated:
        record_badge_progress(current_user, "battle-voter")

    return redirect(url_for(
        "battle.arena",
        f1=f"{f1_type}:{f1_id}",
        f2=f"{f2_type}:{f2_id}",
        voted=arena_vote.id,
    ))


# ─── Team Battles ────────────────────────────────────────────────────────────

@battle_bp.route("/team")
def team_list():
    battles = TeamBattle.query.order_by(TeamBattle.created_at.desc()).limit(20).all()
    return render_template("battle/team_list.html", battles=battles)


@battle_bp.route("/team/new", methods=["GET", "POST"])
def team_new():
    heroes, villains = _all_combatants()

    if request.method == "GET":
        return render_template("battle/team_new.html", heroes=heroes, villains=villains)

    # Parse team members: "hero:1", "villain:3", etc.
    team1_raw = request.form.getlist("team1")
    team2_raw = request.form.getlist("team2")

    def parse_members(raw_list):
        members = []
        for val in raw_list:
            ftype, fid = _parse_fighter_param(val)
            if not ftype:
                continue
            combatant = _get_combatant(ftype, fid)
            if combatant:
                members.append({
                    "type": ftype,
                    "id": fid,
                    "name": combatant["name"],
                    "powers": combatant["powers"],
                    "image_file": combatant["image_file"],
                    "image_folder": combatant["image_folder"],
                    "power_level": combatant["power_level"],
                    "gender": combatant.get("gender", "male"),
                })
        return members

    team1_members = parse_members(team1_raw)
    team2_members = parse_members(team2_raw)

    if len(team1_members) < 2 or len(team2_members) < 2:
        flash("Each team needs at least 2 fighters!", "danger")
        return redirect(url_for("battle.team_new"))

    if len(team1_members) > 3 or len(team2_members) > 3:
        flash("Maximum 3 fighters per team!", "danger")
        return redirect(url_for("battle.team_new"))

    # Check no fighter appears on both teams
    t1_keys = {(m["type"], m["id"]) for m in team1_members}
    t2_keys = {(m["type"], m["id"]) for m in team2_members}
    if t1_keys & t2_keys:
        flash("The same fighter can't be on both teams!", "danger")
        return redirect(url_for("battle.team_new"))

    team1_name = " & ".join(m["name"] for m in team1_members[:2])
    team2_name = " & ".join(m["name"] for m in team2_members[:2])

    battle = TeamBattle(
        team1_name=team1_name,
        team2_name=team2_name,
        team1_members=json.dumps(team1_members),
        team2_members=json.dumps(team2_members),
    )
    db.session.add(battle)
    db.session.commit()

    flash(f"Team battle created! {team1_name} vs {team2_name} — vote now!", "success")
    return redirect(url_for("battle.team_battle", battle_id=battle.id))


@battle_bp.route("/team/<int:battle_id>")
def team_battle(battle_id):
    battle = TeamBattle.query.get_or_404(battle_id)
    team1_members = json.loads(battle.team1_members)
    team2_members = json.loads(battle.team2_members)

    session_key = _get_session_key()
    existing_vote = TeamBattleVote.query.filter_by(
        team_battle_id=battle.id,
        session_key=session_key,
    ).first()

    team1_votes = sum(1 for v in battle.votes if v.winning_team == 1)
    team2_votes = sum(1 for v in battle.votes if v.winning_team == 2)
    total_votes = team1_votes + team2_votes
    team1_pct = round(team1_votes / total_votes * 100) if total_votes else 0
    team2_pct = 100 - team1_pct if total_votes else 0

    narration = None
    last_vote_id = request.args.get("voted", type=int)
    if last_vote_id:
        last_vote = TeamBattleVote.query.get(last_vote_id)
        if last_vote:
            narration = last_vote.narration

    return render_template(
        "battle/team_battle.html",
        battle=battle,
        team1_members=team1_members,
        team2_members=team2_members,
        existing_vote=existing_vote,
        team1_votes=team1_votes,
        team2_votes=team2_votes,
        total_votes=total_votes,
        team1_pct=team1_pct,
        team2_pct=team2_pct,
        narration=narration,
    )


@battle_bp.route("/team/<int:battle_id>/vote", methods=["POST"])
def team_vote(battle_id):
    battle = TeamBattle.query.get_or_404(battle_id)
    winning_team = request.form.get("winning_team", type=int)

    if winning_team not in (1, 2):
        flash("Invalid vote.", "danger")
        return redirect(url_for("battle.team_battle", battle_id=battle_id))

    session_key = _get_session_key()
    existing = TeamBattleVote.query.filter_by(
        team_battle_id=battle.id,
        session_key=session_key,
    ).first()

    if existing:
        flash("You already voted in this team battle!", "info")
        return redirect(url_for("battle.team_battle", battle_id=battle_id))

    team1_members = json.loads(battle.team1_members)
    team2_members = json.loads(battle.team2_members)
    winning_members = team1_members if winning_team == 1 else team2_members
    losing_team_name = battle.team2_name if winning_team == 1 else battle.team1_name
    winning_team_name = battle.team1_name if winning_team == 1 else battle.team2_name

    narration = None
    try:
        narration = generate_team_battle_narration(
            battle.team1_name, team1_members,
            battle.team2_name, team2_members,
            winning_team_name,
        )
    except Exception:
        pass

    tbv = TeamBattleVote(
        team_battle_id=battle.id,
        winning_team=winning_team,
        narration=narration,
        session_key=session_key,
        user_id=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(tbv)
    db.session.commit()

    if current_user.is_authenticated:
        record_badge_progress(current_user, "battle-voter")

    return redirect(url_for("battle.team_battle", battle_id=battle_id, voted=tbv.id))


# ─── Leaderboard ─────────────────────────────────────────────────────────────

@battle_bp.route("/leaderboard")
def leaderboard():
    all_votes = ArenaBattleVote.query.all()

    # Load all heroes and villains for name lookup
    heroes = {c.id: c for c in Character.query.all()}
    villains = {v.id: v for v in Villain.query.all()}

    def get_name(ftype, fid):
        if ftype == "hero":
            h = heroes.get(fid)
            return h.superhero_name if h else f"Hero #{fid}"
        v = villains.get(fid)
        return v.villain_name if v else f"Villain #{fid}"

    def get_obj(ftype, fid):
        if ftype == "hero":
            return heroes.get(fid)
        return villains.get(fid)

    # Per-matchup stats
    matchup_stats = {}
    win_counts = defaultdict(int)
    battle_appearances = defaultdict(int)

    for vote in all_votes:
        key = frozenset([
            (vote.fighter1_type, vote.fighter1_id),
            (vote.fighter2_type, vote.fighter2_id),
        ])
        if key not in matchup_stats:
            matchup_stats[key] = defaultdict(int)
        matchup_stats[key][(vote.winner_type, vote.winner_id)] += 1
        win_counts[(vote.winner_type, vote.winner_id)] += 1
        battle_appearances[(vote.fighter1_type, vote.fighter1_id)] += 1
        battle_appearances[(vote.fighter2_type, vote.fighter2_id)] += 1

    # Build matchup rows
    matchup_rows = []
    for key, counts in matchup_stats.items():
        ids = list(key)
        if len(ids) < 2:
            continue
        f1_type, f1_id = ids[0]
        f2_type, f2_id = ids[1]
        f1_obj = get_obj(f1_type, f1_id)
        f2_obj = get_obj(f2_type, f2_id)
        if not f1_obj or not f2_obj:
            continue
        f1_votes = counts.get((f1_type, f1_id), 0)
        f2_votes = counts.get((f2_type, f2_id), 0)
        total = f1_votes + f2_votes
        matchup_rows.append({
            "fighter1": _get_combatant(f1_type, f1_id),
            "fighter2": _get_combatant(f2_type, f2_id),
            "f1_votes": f1_votes,
            "f2_votes": f2_votes,
            "total_votes": total,
            "f1_pct": round(f1_votes / total * 100) if total else 0,
            "f2_pct": round(f2_votes / total * 100) if total else 0,
            "f1_key": f"{f1_type}:{f1_id}",
            "f2_key": f"{f2_type}:{f2_id}",
        })
    matchup_rows.sort(key=lambda r: r["total_votes"], reverse=True)

    # Build rankings (all heroes + villains ranked by wins)
    rankings = []
    all_fighter_keys = set(win_counts.keys()) | set(battle_appearances.keys())
    for ftype, fid in all_fighter_keys:
        combatant = _get_combatant(ftype, fid)
        if not combatant:
            continue
        wins = win_counts.get((ftype, fid), 0)
        appearances = battle_appearances.get((ftype, fid), 0)
        unique_battles = appearances // 2 if appearances > 0 else 0
        rankings.append({
            "combatant": combatant,
            "wins": wins,
            "battles": unique_battles,
            "win_rate": round(wins / unique_battles * 100) if unique_battles else 0,
        })
    rankings.sort(key=lambda r: (r["wins"], r["win_rate"]), reverse=True)

    # Team battle stats
    recent_team_battles = TeamBattle.query.order_by(TeamBattle.created_at.desc()).limit(5).all()

    return render_template(
        "battle/leaderboard.html",
        matchup_rows=matchup_rows,
        rankings=rankings,
        total_votes_cast=len(all_votes),
        recent_team_battles=recent_team_battles,
    )
