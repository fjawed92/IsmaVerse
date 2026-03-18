from datetime import datetime
from ..extensions import db

REACTION_TYPES = ["boom", "pow", "amazing", "wow", "cool"]

class HeroReaction(db.Model):
    __tablename__ = "hero_reactions"

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey("characters.id"), nullable=False)
    reaction_type = db.Column(db.String(20), nullable=False)
    session_key = db.Column(db.String(64), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    character = db.relationship("Character", back_populates="reactions")

    def __repr__(self):
        return f"<HeroReaction {self.reaction_type} on character {self.character_id}>"
