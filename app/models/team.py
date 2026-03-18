from datetime import datetime
from ..extensions import db


team_members = db.Table(
    "team_members",
    db.Column("team_id", db.Integer, db.ForeignKey("hero_teams.id"), primary_key=True),
    db.Column("character_id", db.Integer, db.ForeignKey("characters.id"), primary_key=True),
)


class HeroTeam(db.Model):
    __tablename__ = "hero_teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slogan = db.Column(db.String(255), nullable=True)
    color = db.Column(db.String(40), nullable=True, default="blue")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    members = db.relationship("Character", secondary=team_members, backref="teams")
    creator = db.relationship("User", backref="created_teams")

    def __repr__(self):
        return f"<HeroTeam {self.id} {self.name}>"
