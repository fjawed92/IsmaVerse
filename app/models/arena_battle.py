"""
Extended battle models that support any combatant type (hero or villain).
"""
from datetime import datetime
from ..extensions import db


class ArenaBattleVote(db.Model):
    """1v1 vote between any two combatants (heroes or villains).
    Uses string type fields instead of FK constraints so both character
    and villain tables can be referenced without schema coupling.
    """
    __tablename__ = "arena_battle_votes"

    id = db.Column(db.Integer, primary_key=True)

    fighter1_type = db.Column(db.String(10), nullable=False)   # 'hero' or 'villain'
    fighter1_id   = db.Column(db.Integer, nullable=False)
    fighter2_type = db.Column(db.String(10), nullable=False)
    fighter2_id   = db.Column(db.Integer, nullable=False)

    winner_type = db.Column(db.String(10), nullable=False)
    winner_id   = db.Column(db.Integer, nullable=False)

    narration   = db.Column(db.Text, nullable=True)   # AI-generated battle story

    session_key = db.Column(db.String(64), nullable=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<ArenaBattleVote "
            f"{self.fighter1_type}:{self.fighter1_id} vs "
            f"{self.fighter2_type}:{self.fighter2_id} "
            f"winner={self.winner_type}:{self.winner_id}>"
        )


class TeamBattle(db.Model):
    """A team vs team matchup.  Members stored as JSON lists."""
    __tablename__ = "team_battles"

    id = db.Column(db.Integer, primary_key=True)

    team1_name    = db.Column(db.String(120), nullable=False, default="Team 1")
    team1_members = db.Column(db.Text, nullable=False)  # JSON: [{"type":"hero","id":1,"name":"..."},...]
    team2_name    = db.Column(db.String(120), nullable=False, default="Team 2")
    team2_members = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    votes = db.relationship("TeamBattleVote", back_populates="battle", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TeamBattle {self.id} {self.team1_name} vs {self.team2_name}>"


class TeamBattleVote(db.Model):
    __tablename__ = "team_battle_votes"

    id             = db.Column(db.Integer, primary_key=True)
    team_battle_id = db.Column(db.Integer, db.ForeignKey("team_battles.id"), nullable=False)
    winning_team   = db.Column(db.Integer, nullable=False)  # 1 or 2
    narration      = db.Column(db.Text, nullable=True)
    session_key    = db.Column(db.String(64), nullable=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    battle = db.relationship("TeamBattle", back_populates="votes")

    def __repr__(self):
        return f"<TeamBattleVote battle={self.team_battle_id} winner=team{self.winning_team}>"
