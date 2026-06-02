from datetime import datetime

from ..extensions import db
from ..models.badge import Badge, UserBadge

BADGE_DEFINITIONS = {
    # Original 4
    "comic-reader": {
        "name": "Read 3 Comics",
        "description": "Read three comics.",
        "unlock_count": 3,
        "color": "yellow",
        "emoji": "📖",
    },
    "character-explorer": {
        "name": "Hero Explorer",
        "description": "Visited the Characters page.",
        "unlock_count": 1,
        "color": "green",
        "emoji": "🦸",
    },
    "hero-maker": {
        "name": "Hero Creator",
        "description": "Created a new hero.",
        "unlock_count": 1,
        "color": "pink",
        "emoji": "✨",
    },
    "secret-visitor": {
        "name": "Secret Badge",
        "description": "Visited IsmaVerse multiple times.",
        "unlock_count": 5,
        "color": "blue",
        "emoji": "🔮",
    },
    # New badges
    "super-reader": {
        "name": "Super Reader",
        "description": "Read 10 comics total!",
        "unlock_count": 10,
        "color": "red",
        "emoji": "🚀",
    },
    "villain-maker": {
        "name": "Villain Creator",
        "description": "Created a fearsome villain.",
        "unlock_count": 1,
        "color": "purple",
        "emoji": "😈",
    },
    "team-player": {
        "name": "Team Player",
        "description": "Built a hero team.",
        "unlock_count": 1,
        "color": "blue",
        "emoji": "🤝",
    },
    "reactor": {
        "name": "Reactor",
        "description": "Reacted to 5 heroes.",
        "unlock_count": 5,
        "color": "yellow",
        "emoji": "💥",
    },
    "commentator": {
        "name": "Commentator",
        "description": "Left a comment on a hero.",
        "unlock_count": 1,
        "color": "green",
        "emoji": "💬",
    },
    "battle-voter": {
        "name": "Battle Voter",
        "description": "Voted in 3 hero battles.",
        "unlock_count": 3,
        "color": "red",
        "emoji": "⚔️",
    },
    "fan-artist": {
        "name": "Fan Artist",
        "description": "Uploaded fan art to the gallery.",
        "unlock_count": 1,
        "color": "pink",
        "emoji": "🎨",
    },
    "quiz-master": {
        "name": "Quiz Champ",
        "description": "Completed the superpower quiz.",
        "unlock_count": 1,
        "color": "yellow",
        "emoji": "🏆",
    },
    "mission-ace": {
        "name": "Mission Ace",
        "description": "Checked in 5 daily missions.",
        "unlock_count": 5,
        "color": "green",
        "emoji": "🎯",
    },
    "true-fan": {
        "name": "True Fan",
        "description": "Visited IsmaVerse 20 times!",
        "unlock_count": 20,
        "color": "blue",
        "emoji": "⭐",
    },
    "power-up": {
        "name": "Power Up!",
        "description": "Created 3 heroes.",
        "unlock_count": 3,
        "color": "red",
        "emoji": "💪",
    },
    # Profiles / favorites / streaks / games
    "collector": {
        "name": "Collector",
        "description": "Favorited your first hero, villain or comic.",
        "unlock_count": 1,
        "color": "pink",
        "emoji": "❤️",
    },
    "streak-3": {
        "name": "On Fire!",
        "description": "Visited 3 days in a row.",
        "unlock_count": 1,
        "color": "red",
        "emoji": "🔥",
    },
    "streak-7": {
        "name": "Week Warrior",
        "description": "Kept a 7-day reading streak!",
        "unlock_count": 1,
        "color": "yellow",
        "emoji": "🗓️",
    },
    "game-player": {
        "name": "Game On!",
        "description": "Played a mini-game.",
        "unlock_count": 1,
        "color": "green",
        "emoji": "🕹️",
    },
    "arcade-ace": {
        "name": "Arcade Ace",
        "description": "Played an arcade game.",
        "unlock_count": 1,
        "color": "blue",
        "emoji": "👾",
    },
    "high-flyer": {
        "name": "High Flyer",
        "description": "Scored 100+ in an arcade game.",
        "unlock_count": 1,
        "color": "yellow",
        "emoji": "🏅",
    },
    "hero-champion": {
        "name": "Hero Champion",
        "description": "Claimed a hero as your champion.",
        "unlock_count": 1,
        "color": "pink",
        "emoji": "🦸",
    },
}


def ensure_badges() -> None:
    existing = {badge.slug: badge for badge in Badge.query.all()}
    created = False

    for slug, data in BADGE_DEFINITIONS.items():
        if slug in existing:
            continue
        badge = Badge(
            slug=slug,
            name=data["name"],
            description=data.get("description"),
        )
        db.session.add(badge)
        created = True

    if created:
        db.session.commit()


def _get_badge(slug: str) -> Badge:
    ensure_badges()
    badge = Badge.query.filter_by(slug=slug).first()
    if not badge:
        raise ValueError(f"Badge '{slug}' is not configured.")
    return badge


def record_badge_progress(user, slug: str, increment: int = 1) -> None:
    if slug not in BADGE_DEFINITIONS:
        return
    badge = _get_badge(slug)
    unlock_target = BADGE_DEFINITIONS[slug]["unlock_count"]

    user_badge = UserBadge.query.filter_by(user_id=user.id, badge_id=badge.id).first()
    if not user_badge:
        user_badge = UserBadge(user_id=user.id, badge_id=badge.id, progress_count=0)

    if user_badge.unlocked_at:
        return

    user_badge.progress_count += increment
    if user_badge.progress_count >= unlock_target:
        user_badge.unlocked_at = datetime.utcnow()

    db.session.add(user_badge)
    db.session.commit()


def get_user_badge_states(user) -> dict:
    ensure_badges()
    badges = Badge.query.all()
    user_badges = {
        badge.badge_id: badge
        for badge in UserBadge.query.filter_by(user_id=user.id).all()
    }

    states = {}
    for badge in badges:
        user_badge = user_badges.get(badge.id)
        states[badge.slug] = bool(user_badge and user_badge.unlocked_at)
    return states


def get_badge_meta() -> dict:
    return BADGE_DEFINITIONS
