"""Kid profiles, avatars and favorites.

Logged-in users persist to the database (UserProfile / Favorite).
Anonymous users use a localStorage mirror handled in main.js — the
templates render identical markup driven by a ``data-fav-source`` flag,
exactly like the existing badge dual-source pattern.
"""

from ..extensions import db
from ..models.profile import UserProfile, Favorite
from ..models.character import Character
from ..models.villain import Villain
from ..models.comic import Comic

# Built-in, kid-safe avatars (no uploads). slug -> (emoji, label).
AVATARS = [
    ("lightning", "⚡", "Lightning"),
    ("star",      "⭐", "Star"),
    ("rocket",    "🚀", "Rocket"),
    ("dino",      "🦖", "Dino"),
    ("robot",     "🤖", "Robot"),
    ("unicorn",   "🦄", "Unicorn"),
    ("fox",       "🦊", "Fox"),
    ("alien",     "👽", "Alien"),
    ("ninja",     "🥷", "Ninja"),
    ("wizard",    "🧙", "Wizard"),
    ("cat",       "🐱", "Cat"),
    ("dragon",    "🐉", "Dragon"),
]

AVATAR_EMOJI = {slug: emoji for slug, emoji, _ in AVATARS}

VALID_ITEM_TYPES = {"hero", "villain", "comic"}


def get_or_create_profile(user) -> UserProfile:
    """Return the user's profile, creating a blank one on first access."""
    profile = UserProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    return profile


def is_favorited(user, item_type: str, item_id: int) -> bool:
    return (
        Favorite.query.filter_by(
            user_id=user.id, item_type=item_type, item_id=item_id
        ).first()
        is not None
    )


def toggle_favorite(user, item_type: str, item_id: int) -> bool:
    """Add or remove a favorite. Returns the new favorited state."""
    if item_type not in VALID_ITEM_TYPES:
        raise ValueError(f"Unknown favorite type: {item_type}")

    existing = Favorite.query.filter_by(
        user_id=user.id, item_type=item_type, item_id=item_id
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return False

    db.session.add(
        Favorite(user_id=user.id, item_type=item_type, item_id=item_id)
    )
    db.session.commit()
    return True


def get_favorite_keys(user) -> set:
    """Set of ``"type:id"`` strings — handy for marking buttons as active."""
    return {
        f"{fav.item_type}:{fav.item_id}"
        for fav in Favorite.query.filter_by(user_id=user.id).all()
    }


def get_favorites(user) -> dict:
    """Resolve a user's favorites into live objects, grouped by type."""
    favs = Favorite.query.filter_by(user_id=user.id).order_by(
        Favorite.created_at.desc()
    ).all()

    heroes_ids   = [f.item_id for f in favs if f.item_type == "hero"]
    villains_ids = [f.item_id for f in favs if f.item_type == "villain"]
    comics_ids   = [f.item_id for f in favs if f.item_type == "comic"]

    heroes   = Character.query.filter(Character.id.in_(heroes_ids)).all() if heroes_ids else []
    villains = Villain.query.filter(Villain.id.in_(villains_ids)).all() if villains_ids else []
    comics   = Comic.query.filter(Comic.id.in_(comics_ids)).all() if comics_ids else []

    return {"heroes": heroes, "villains": villains, "comics": comics}
