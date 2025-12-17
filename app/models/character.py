from datetime import datetime
from ..extensions import db

class Character(db.Model):
    __tablename__ = "characters"

    id = db.Column(db.Integer, primary_key=True)

    superhero_name = db.Column(db.String(120), nullable=False)
    powers = db.Column(db.Text, nullable=True)
    weakness = db.Column(db.Text, nullable=True)
    origins = db.Column(db.Text, nullable=True)
    image_file = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Character {self.id} {self.superhero_name}>"
