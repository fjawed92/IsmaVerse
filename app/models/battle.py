from datetime import datetime
from ..extensions import db


class BattleVote(db.Model):
    __tablename__ = "battle_votes"

    id = db.Column(db.Integer, primary_key=True)
    hero1_id = db.Column(db.Integer, db.ForeignKey("characters.id"), nullable=False)
    hero2_id = db.Column(db.Integer, db.ForeignKey("characters.id"), nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey("characters.id"), nullable=False)
    session_key = db.Column(db.String(64), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    hero1 = db.relationship("Character", foreign_keys=[hero1_id])
    hero2 = db.relationship("Character", foreign_keys=[hero2_id])
    winner = db.relationship("Character", foreign_keys=[winner_id])

    def __repr__(self):
        return f"<BattleVote hero1={self.hero1_id} hero2={self.hero2_id} winner={self.winner_id}>"
