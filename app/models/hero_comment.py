from datetime import datetime
from ..extensions import db


class HeroComment(db.Model):
    __tablename__ = "hero_comments"

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey("characters.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    character = db.relationship("Character", back_populates="hero_comments")
    author = db.relationship("User", back_populates="hero_comments")

    def __repr__(self):
        return f"<HeroComment by user {self.user_id} on character {self.character_id}>"
