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
    image_prompt = db.Column(db.Text, nullable=True)

    costume_color = db.Column(db.String(80), nullable=True)
    boots_color = db.Column(db.String(80), nullable=True)
    gloves_color = db.Column(db.String(80), nullable=True)
    chest_symbol = db.Column(db.String(120), nullable=True)
    eye_mask_color = db.Column(db.String(80), nullable=True)
    cape_color = db.Column(db.String(80), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    hair_color = db.Column(db.String(80), nullable=True)

    gender = db.Column(db.String(10), nullable=True, default="male")  # 'male' or 'female'

    power_level_override = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    reactions = db.relationship("HeroReaction", back_populates="character", cascade="all, delete-orphan")
    hero_comments = db.relationship("HeroComment", back_populates="character", cascade="all, delete-orphan")

    @property
    def power_level(self):
        if self.power_level_override is not None:
            return max(10, min(self.power_level_override, 100))
        score = 50
        if self.powers:
            score += min(len(self.powers.split()), 20) * 2
        if self.weakness:
            score -= min(len(self.weakness.split()), 10) * 1
        if self.age:
            score += max(0, 16 - self.age) * 1
        total_reactions = len(self.reactions)
        score += min(total_reactions * 2, 30)
        return max(10, min(score, 100))

    @property
    def reaction_counts(self):
        counts = {"boom": 0, "pow": 0, "amazing": 0, "wow": 0, "cool": 0}
        for r in self.reactions:
            if r.reaction_type in counts:
                counts[r.reaction_type] += 1
        return counts

    def __repr__(self) -> str:
        return f"<Character {self.id} {self.superhero_name}>"
