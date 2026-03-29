from datetime import datetime
from ..extensions import db


class Villain(db.Model):
    __tablename__ = "villains"

    id = db.Column(db.Integer, primary_key=True)

    villain_name = db.Column(db.String(120), nullable=False)
    powers = db.Column(db.Text, nullable=True)
    weakness = db.Column(db.Text, nullable=True)
    evil_plan = db.Column(db.Text, nullable=True)
    image_file = db.Column(db.String(255), nullable=True)
    image_prompt = db.Column(db.Text, nullable=True)

    costume_color = db.Column(db.String(80), nullable=True)
    lair_location = db.Column(db.String(120), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    hair_color = db.Column(db.String(80), nullable=True)

    power_level_override = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def power_level(self) -> int:
        if self.power_level_override is not None:
            return max(10, min(self.power_level_override, 100))
        score = 50
        if self.powers:
            score += min(len(self.powers.split()), 20) * 2
        if self.weakness:
            score -= min(len(self.weakness.split()), 10)
        if self.evil_plan:
            score += min(len(self.evil_plan.split()), 10)
        if self.age:
            score -= max(0, self.age - 30) // 10
        return max(10, min(score, 100))

    def __repr__(self):
        return f"<Villain {self.id} {self.villain_name}>"
