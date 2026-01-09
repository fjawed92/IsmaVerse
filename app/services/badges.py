from datetime import datetime

from ..extensions import db
from ..models.badge import Badge, UserBadge

BADGE_DEFINITIONS = {
    "comic-reader": {
        "name": "Read 3 Comics",
        "description": "Read three comics.",
        "unlock_count": 3,
    },
    "character-explorer": {
        "name": "Visited Characters",
        "description": "Visited the Characters page.",
        "unlock_count": 1,
    },
    "hero-maker": {
        "name": "Created a Hero",
        "description": "Created a new hero.",
        "unlock_count": 1,
    },
    "secret-visitor": {
        "name": "Secret Badge",
        "description": "Visited IsmaVerse multiple times.",
        "unlock_count": 5,
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
