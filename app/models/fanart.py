from datetime import datetime
from ..extensions import db


class FanArt(db.Model):
    __tablename__ = "fan_arts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    artist_name = db.Column(db.String(80), nullable=False)
    image_file = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    uploader = db.relationship("User", backref="fan_arts")

    def __repr__(self):
        return f"<FanArt {self.id} '{self.title}' by {self.artist_name}>"
