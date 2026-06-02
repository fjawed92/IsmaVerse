"""Arcade games: scores, leaderboards and hero champions.

Logged-in users persist scores (GameScore) and a one-to-one champion
(GameChampion). Anonymous players keep only a local best in localStorage
(handled in games.js) and never appear on the global leaderboard.

The champion's level / power tier is *cosmetic* — derived from accumulated
XP and shown on the leaderboard and profile. It never feeds back into the
game's difficulty.
"""

from sqlalchemy import func

from ..extensions import db
from ..models.game import GameScore, GameChampion
from ..models.user import User
from ..models.character import Character
from .badges import record_badge_progress

# Single source of truth for valid game slugs + their display names.
GAME_SLUGS = {
    "poppi-jump": "Poppi Jump",
    "spaceship": "Spaceship Dodge",
}

MAX_LEVEL = 50

# Power tiers by level — name + emoji shown as a badge on the leaderboard.
_TIERS = [
    (20, {"name": "Legend", "emoji": "🌟"}),
    (10, {"name": "Champion", "emoji": "🏆"}),
    (5, {"name": "Hero", "emoji": "🦸"}),
    (1, {"name": "Rookie", "emoji": "🔰"}),
]


def get_or_create_champion(user) -> GameChampion:
    """Return the user's champion record, creating a blank one on first access."""
    champ = GameChampion.query.filter_by(user_id=user.id).first()
    if not champ:
        champ = GameChampion(user_id=user.id)
        db.session.add(champ)
        db.session.commit()
    return champ


def compute_level(xp: int) -> int:
    """Cosmetic level from accumulated XP. Gently escalating, capped."""
    if xp <= 0:
        return 1
    return min(MAX_LEVEL, int((xp / 50) ** 0.5) + 1)


def tier_for_level(level: int) -> dict:
    """Power tier {name, emoji} for a given level."""
    for threshold, tier in _TIERS:
        if level >= threshold:
            return tier
    return _TIERS[-1][1]


def submit_score(user, game: str, score) -> dict:
    """Record a score and grow the champion's cosmetic XP/level.

    Raises ValueError on an unknown game slug or a non-numeric/negative score.
    Returns a dict the JS reacts to: best, rank, level, level_up, tier.
    """
    if game not in GAME_SLUGS:
        raise ValueError(f"Unknown game: {game}")
    try:
        score = int(score)
    except (TypeError, ValueError):
        raise ValueError("Score must be a whole number.")
    if score < 0:
        raise ValueError("Score must be non-negative.")

    db.session.add(GameScore(user_id=user.id, game=game, score=score))

    champ = get_or_create_champion(user)
    old_level = champ.level
    champ.xp += 10 + (score // 10)
    champ.games_played += 1
    champ.total_score += score
    champ.level = compute_level(champ.xp)
    db.session.add(champ)
    db.session.commit()

    # Badges (preserve the original game-player behaviour, add arcade ones).
    record_badge_progress(user, "game-player")
    record_badge_progress(user, "arcade-ace")
    if score >= 100:
        record_badge_progress(user, "high-flyer")

    return {
        "best": get_user_best(user, game),
        "rank": _rank_for_score(game, score),
        "level": champ.level,
        "level_up": champ.level > old_level,
        "tier": tier_for_level(champ.level),
    }


def get_user_best(user, game: str) -> int:
    best = (
        db.session.query(func.max(GameScore.score))
        .filter(GameScore.user_id == user.id, GameScore.game == game)
        .scalar()
    )
    return int(best or 0)


def _rank_for_score(game: str, score: int) -> int:
    """1-based rank of a score among each user's personal best for this game."""
    best_per_user = (
        db.session.query(func.max(GameScore.score).label("best"))
        .filter(GameScore.game == game)
        .group_by(GameScore.user_id)
        .subquery()
    )
    ahead = (
        db.session.query(func.count())
        .select_from(best_per_user)
        .filter(best_per_user.c.best > score)
        .scalar()
    )
    return int(ahead or 0) + 1


def get_leaderboard(game: str, limit: int = 10) -> list:
    """Top-N players for a game by their personal best score.

    Anonymous players have no GameScore rows, so they never appear here.
    """
    if game not in GAME_SLUGS:
        return []

    best_per_user = (
        db.session.query(
            GameScore.user_id.label("user_id"),
            func.max(GameScore.score).label("best"),
        )
        .filter(GameScore.game == game)
        .group_by(GameScore.user_id)
        .subquery()
    )

    rows = (
        db.session.query(
            best_per_user.c.best,
            User.username,
            GameChampion.level,
            Character.superhero_name,
            Character.image_file,
        )
        .join(User, User.id == best_per_user.c.user_id)
        .outerjoin(GameChampion, GameChampion.user_id == best_per_user.c.user_id)
        .outerjoin(Character, Character.id == GameChampion.character_id)
        .order_by(best_per_user.c.best.desc(), User.username.asc())
        .limit(limit)
        .all()
    )

    board = []
    for i, (best, username, level, hero_name, hero_img) in enumerate(rows, start=1):
        lvl = level or 1
        board.append({
            "rank": i,
            "username": username,
            "score": int(best or 0),
            "champion_name": hero_name,
            "champion_image": hero_img,
            "level": lvl,
            "tier": tier_for_level(lvl),
        })
    return board


def claim_champion(user, character_id) -> GameChampion:
    """Claim (or change) the hero a user represents. Raises ValueError if the
    hero doesn't exist."""
    try:
        character_id = int(character_id)
    except (TypeError, ValueError):
        raise ValueError("Pick a hero to be your champion.")

    character = Character.query.get(character_id)
    if not character:
        raise ValueError("That hero doesn't exist.")

    champ = get_or_create_champion(user)
    champ.character_id = character.id
    db.session.add(champ)
    db.session.commit()

    record_badge_progress(user, "hero-champion")
    return champ


def get_champion_view(user):
    """Resolved champion for the profile / leaderboard, or None if none yet."""
    champ = GameChampion.query.filter_by(user_id=user.id).first()
    if not champ:
        return None
    return {
        "character": champ.character,            # Character or None
        "level": champ.level,
        "tier": tier_for_level(champ.level),
        "xp": champ.xp,
        "games_played": champ.games_played,
        "total_score": champ.total_score,
    }
