from datetime import datetime

from ..extensions import db


class UserProfile(db.Model):
    """One-to-one kid profile: a chosen avatar + display name + theme echo."""

    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    avatar = db.Column(db.String(40), nullable=True)        # built-in avatar slug
    display_name = db.Column(db.String(80), nullable=True)
    theme = db.Column(db.String(20), nullable=False, default="system")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = db.relationship("User", back_populates="profile")


class Favorite(db.Model):
    """A favorited hero / villain / comic. String-typed polymorphism mirrors
    the (type, id) combatant pattern already used by the battle arena."""

    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    item_type = db.Column(db.String(20), nullable=False)    # hero | villain | comic
    item_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="favorites")

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "item_type", "item_id", name="uq_favorite"
        ),
    )


class ReadingStreak(db.Model):
    """One-to-one daily streak tracker for logged-in kids."""

    __tablename__ = "reading_streaks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    current_streak = db.Column(db.Integer, nullable=False, default=0)
    longest_streak = db.Column(db.Integer, nullable=False, default=0)
    last_active_date = db.Column(db.Date, nullable=True)
    total_active_days = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = db.relationship("User", back_populates="streak")
