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


def _calculate_winner(fighter1: dict, fighter2: dict) -> tuple[dict, dict, bool]:
    """Weighted random — higher power_level = better odds. Returns (winner, loser, upset).

    A lucky factor of ±15 is added to each fighter's power level so that
    upsets are always possible, keeping the battles exciting for kids.
    """
    pl1 = fighter1["power_level"]
    pl2 = fighter2["power_level"]
    eff1 = max(1, pl1 + random.randint(-15, 15))
    eff2 = max(1, pl2 + random.randint(-15, 15))
    if random.random() * (eff1 + eff2) < eff1:
        winner, loser = fighter1, fighter2
    else:
        winner, loser = fighter2, fighter1
    upset = winner["power_level"] < loser["power_level"]
    return winner, loser, upset


def _update_power_level(fighter_type: str, fighter_id: int, delta: int) -> int:
    """Persist a power level change. Returns the new level."""
    if fighter_type == "hero":
        char = Character.query.get(fighter_id)
        if char:
            new_level = max(10, min(100, char.power_level + delta))
            char.power_level_override = new_level
            return new_level
    elif fighter_type == "villain":
        vil = Villain.query.get(fighter_id)
        if vil:
            new_level = max(10, min(100, vil.power_level + delta))
            vil.power_level_override = new_level
            return new_level
    return 0


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
            win_counts={}, total_battles=0,
            fighter1_pct=0, fighter2_pct=0,
            narration=None,
            battle_result=None,
            already_fought=False,
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
        picks = random.sample(all_combatants, 2)
        fighter1 = _get_combatant(picks[0]["type"], picks[0]["id"])
        fighter2 = _get_combatant(picks[1]["type"], picks[1]["id"])

    # Win counts for this matchup (from all-time battle history)
    all_battles = ArenaBattleVote.query.filter(
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
    win_counts = {f1_key: 0, f2_key: 0}
    for b in all_battles:
        key = (b.winner_type, b.winner_id)
        if key in win_counts:
            win_counts[key] += 1

    total_battles = len(all_battles)
    f1_pct = round(win_counts[f1_key] / total_battles * 100) if total_battles else 0
    f2_pct = 100 - f1_pct if total_battles else 0

    # Check if this session already fought this matchup
    session_key = _get_session_key()
    already_fought = bool(ArenaBattleVote.query.filter(
        ArenaBattleVote.session_key == session_key,
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
    ).first())

    # Show narration + result after a fight
    narration = None
    battle_result = None
    fought_id = request.args.get("fought", type=int)
    if fought_id:
        fought = ArenaBattleVote.query.get(fought_id)
        if fought:
            narration = fought.narration
            battle_result = {
                "winner_key": f"{fought.winner_type}:{fought.winner_id}",
                "gain": request.args.get("gain", type=int, default=0),
                "loss": request.args.get("loss", type=int, default=0),
                "upset": request.args.get("upset", type=int, default=0) == 1,
            }

    return render_template(
        "battle/arena.html",
        fighter1=fighter1,
        fighter2=fighter2,
        all_combatants=all_combatants,
        win_counts=win_counts,
        total_battles=total_battles,
        fighter1_pct=f1_pct,
        fighter2_pct=f2_pct,
        narration=narration,
        battle_result=battle_result,
        already_fought=already_fought,
        f1_key=f"{fighter1['type']}:{fighter1['id']}",
        f2_key=f"{fighter2['type']}:{fighter2['id']}",
    )


@battle_bp.route("/fight", methods=["POST"])
def fight():
    f1_type = request.form.get("f1_type", "")
    f1_id   = request.form.get("f1_id", type=int)
    f2_type = request.form.get("f2_type", "")
    f2_id   = request.form.get("f2_id", type=int)

    if not all([f1_type, f1_id, f2_type, f2_id]):
        flash("Invalid battle.", "danger")
        return redirect(url_for("battle.arena"))

    session_key = _get_session_key()

    # Once per session per matchup
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
        flash("You already fought this matchup! Pick a new one!", "info")
        return redirect(url_for("battle.arena", f1=f"{f1_type}:{f1_id}", f2=f"{f2_type}:{f2_id}"))

    fighter1 = _get_combatant(f1_type, f1_id)
    fighter2 = _get_combatant(f2_type, f2_id)
    if not fighter1 or not fighter2:
        flash("Fighters not found.", "danger")
        return redirect(url_for("battle.arena"))

    winner, loser, upset = _calculate_winner(fighter1, fighter2)

    win_gain  = random.randint(2, 5)
    loss_drop = random.randint(1, 3)
    _update_power_level(winner["type"], winner["id"],  win_gain)
    _update_power_level(loser["type"],  loser["id"],  -loss_drop)

    # Gather all-time win counts for each fighter for the AI context
    all_fights = ArenaBattleVote.query.filter(
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
    ).all()
    f1_wins_count = sum(1 for b in all_fights if b.winner_type == f1_type and b.winner_id == f1_id)
    f2_wins_count = sum(1 for b in all_fights if b.winner_type == f2_type and b.winner_id == f2_id)

    narration = None
    try:
        narration = generate_battle_narration(
            fighter1["name"], fighter1["powers"],
            fighter2["name"], fighter2["powers"],
            winner["name"],
            fighter1_type=fighter1["type"],
            fighter2_type=fighter2["type"],
            fighter1_gender=fighter1.get("gender", "male"),
            fighter2_gender=fighter2.get("gender", "male"),
            fighter1_wins=f1_wins_count,
            fighter2_wins=f2_wins_count,
            upset=upset,
        )
    except Exception:
        pass

    arena_vote = ArenaBattleVote(
        fighter1_type=f1_type, fighter1_id=f1_id,
        fighter2_type=f2_type, fighter2_id=f2_id,
        winner_type=winner["type"], winner_id=winner["id"],
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
        fought=arena_vote.id,
        gain=win_gain,
        loss=loss_drop,
        upset=1 if upset else 0,
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

    flash(f"Team battle created! {team1_name} vs {team2_name} — press FIGHT to launch it!", "success")
    return redirect(url_for("battle.team_battle", battle_id=battle.id))


@battle_bp.route("/team/<int:battle_id>")
def team_battle(battle_id):
    battle = TeamBattle.query.get_or_404(battle_id)
    team1_members = json.loads(battle.team1_members)
    team2_members = json.loads(battle.team2_members)

    session_key = _get_session_key()
    already_fought = bool(TeamBattleVote.query.filter_by(
        team_battle_id=battle.id,
        session_key=session_key,
    ).first())

    team1_wins = sum(1 for v in battle.votes if v.winning_team == 1)
    team2_wins = sum(1 for v in battle.votes if v.winning_team == 2)
    total_battles = team1_wins + team2_wins
    team1_pct = round(team1_wins / total_battles * 100) if total_battles else 0
    team2_pct = 100 - team1_pct if total_battles else 0

    narration = None
    battle_result = None
    fought_id = request.args.get("fought", type=int)
    if fought_id:
        fought_vote = TeamBattleVote.query.get(fought_id)
        if fought_vote:
            narration = fought_vote.narration
            battle_result = {
                "winning_team": fought_vote.winning_team,
                "gain": request.args.get("gain", type=int, default=0),
                "loss": request.args.get("loss", type=int, default=0),
                "upset": request.args.get("upset", type=int, default=0) == 1,
            }

    return render_template(
        "battle/team_battle.html",
        battle=battle,
        team1_members=team1_members,
        team2_members=team2_members,
        already_fought=already_fought,
        team1_wins=team1_wins,
        team2_wins=team2_wins,
        total_battles=total_battles,
        team1_pct=team1_pct,
        team2_pct=team2_pct,
        narration=narration,
        battle_result=battle_result,
    )


@battle_bp.route("/team/<int:battle_id>/fight", methods=["POST"])
def team_fight(battle_id):
    battle = TeamBattle.query.get_or_404(battle_id)
    session_key = _get_session_key()

    existing = TeamBattleVote.query.filter_by(
        team_battle_id=battle.id,
        session_key=session_key,
    ).first()
    if existing:
        flash("This team battle has already been fought! Create a new one!", "info")
        return redirect(url_for("battle.team_battle", battle_id=battle_id))

    team1_members = json.loads(battle.team1_members)
    team2_members = json.loads(battle.team2_members)

    # Average power level per team
    avg1 = sum(m["power_level"] for m in team1_members) / len(team1_members)
    avg2 = sum(m["power_level"] for m in team2_members) / len(team2_members)

    # Lucky factor keeps upsets possible
    eff1 = max(1, avg1 + random.randint(-15, 15))
    eff2 = max(1, avg2 + random.randint(-15, 15))
    winning_team = 1 if random.random() * (eff1 + eff2) < eff1 else 2
    upset = (winning_team == 1 and avg1 < avg2) or (winning_team == 2 and avg2 < avg1)

    win_gain  = random.randint(2, 4)
    loss_drop = random.randint(1, 2)
    winning_members = team1_members if winning_team == 1 else team2_members
    losing_members  = team2_members if winning_team == 1 else team1_members
    for m in winning_members:
        _update_power_level(m["type"], m["id"],  win_gain)
    for m in losing_members:
        _update_power_level(m["type"], m["id"], -loss_drop)

    winning_team_name = battle.team1_name if winning_team == 1 else battle.team2_name

    narration = None
    try:
        narration = generate_team_battle_narration(
            battle.team1_name, team1_members,
            battle.team2_name, team2_members,
            winning_team_name,
            upset=upset,
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

    return redirect(url_for(
        "battle.team_battle",
        battle_id=battle_id,
        fought=tbv.id,
        gain=win_gain,
        loss=loss_drop,
        upset=1 if upset else 0,
    ))


# ─── Leaderboard ─────────────────────────────────────────────────────────────

@battle_bp.route("/leaderboard")
def leaderboard():
    all_votes = ArenaBattleVote.query.all()

    heroes = {c.id: c for c in Character.query.all()}
    villains = {v.id: v for v in Villain.query.all()}

    def get_obj(ftype, fid):
        if ftype == "hero":
            return heroes.get(fid)
        return villains.get(fid)

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
        f1_wins = counts.get((f1_type, f1_id), 0)
        f2_wins = counts.get((f2_type, f2_id), 0)
        total = f1_wins + f2_wins
        matchup_rows.append({
            "fighter1": _get_combatant(f1_type, f1_id),
            "fighter2": _get_combatant(f2_type, f2_id),
            "f1_votes": f1_wins,
            "f2_votes": f2_wins,
            "total_votes": total,
            "f1_pct": round(f1_wins / total * 100) if total else 0,
            "f2_pct": round(f2_wins / total * 100) if total else 0,
            "f1_key": f"{f1_type}:{f1_id}",
            "f2_key": f"{f2_type}:{f2_id}",
        })
    matchup_rows.sort(key=lambda r: r["total_votes"], reverse=True)

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

    recent_team_battles = TeamBattle.query.order_by(TeamBattle.created_at.desc()).limit(5).all()

    return render_template(
        "battle/leaderboard.html",
        matchup_rows=matchup_rows,
        rankings=rankings,
        total_votes_cast=len(all_votes),
        recent_team_battles=recent_team_battles,
    )
