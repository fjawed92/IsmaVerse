from datetime import datetime

from ..extensions import db


class GameScore(db.Model):
    """A single score a logged-in kid earned in an arcade mini-game.

    ``game`` is a slug string (see ``GAME_SLUGS`` in services/games.py),
    mirroring the (type, id) string-polymorphism used by Favorite.
    """

    __tablename__ = "game_scores"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    game = db.Column(db.String(40), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="game_scores")

    __table_args__ = (
        db.Index("ix_gamescore_game_score", "game", "score"),
    )


class GameChampion(db.Model):
    """One-to-one champion a kid claims for the arcade.

    The champion is one of the existing roster heroes (Character). It earns
    cosmetic XP / levels as more games are played — purely for show on the
    leaderboard and profile, never fed back into gameplay difficulty.
    """

    __tablename__ = "game_champions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    # Nullable so XP can exist before a hero is claimed, and so a deleted
    # character degrades gracefully (mirrors how Favorite resolves heroes).
    character_id = db.Column(
        db.Integer, db.ForeignKey("characters.id"), nullable=True
    )
    xp = db.Column(db.Integer, nullable=False, default=0)
    level = db.Column(db.Integer, nullable=False, default=1)
    games_played = db.Column(db.Integer, nullable=False, default=0)
    total_score = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = db.relationship("User", back_populates="champion")
    character = db.relationship("Character")
