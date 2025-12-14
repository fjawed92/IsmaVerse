from ..extensions import db

class Comic(db.Model):
    __tablename__ = "comics"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)  # filename stored in static/img/comics/
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    pdf_file = db.Column(db.String(255), nullable=True)
