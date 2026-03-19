from datetime import datetime
from ..extensions import db

# Association table: which heroes star in which story arc
arc_heroes = db.Table(
    "arc_heroes",
    db.Column("arc_id", db.Integer, db.ForeignKey("story_arcs.id"), primary_key=True),
    db.Column("character_id", db.Integer, db.ForeignKey("characters.id"), primary_key=True),
)

# Association table: which villains appear in which story arc
arc_villains = db.Table(
    "arc_villains",
    db.Column("arc_id", db.Integer, db.ForeignKey("story_arcs.id"), primary_key=True),
    db.Column("villain_id", db.Integer, db.ForeignKey("villains.id"), primary_key=True),
)


class StoryArc(db.Model):
    """A multi-issue story arc in the IsmaVerse comic universe."""
    __tablename__ = "story_arcs"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    tagline = db.Column(db.String(300), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)  # AI-generated cover
    arc_number = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(30), nullable=False, default="ongoing")  # ongoing | complete
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    heroes = db.relationship("Character", secondary=arc_heroes, backref="story_arcs", lazy="subquery")
    villains = db.relationship("Villain", secondary=arc_villains, backref="story_arcs", lazy="subquery")
    issues = db.relationship("ComicIssue", back_populates="arc", cascade="all, delete-orphan", order_by="ComicIssue.issue_number")

    def __repr__(self):
        return f"<StoryArc {self.arc_number}: {self.title}>"


class ComicIssue(db.Model):
    """A single comic issue inside a StoryArc."""
    __tablename__ = "comic_issues"

    id = db.Column(db.Integer, primary_key=True)
    arc_id = db.Column(db.Integer, db.ForeignKey("story_arcs.id"), nullable=False)
    issue_number = db.Column(db.Integer, nullable=False, default=1)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    story_text = db.Column(db.Text, nullable=True)  # full prose narrative shown in reader
    cover_image = db.Column(db.String(255), nullable=True)  # AI-generated cover
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    arc = db.relationship("StoryArc", back_populates="issues")
    panels = db.relationship("ComicPanel", back_populates="issue", cascade="all, delete-orphan", order_by="ComicPanel.panel_number")

    def __repr__(self):
        return f"<ComicIssue arc={self.arc_id} issue={self.issue_number}: {self.title}>"


class ComicPanel(db.Model):
    """A single panel within a ComicIssue — AI-generated image + dialogue."""
    __tablename__ = "comic_panels"

    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("comic_issues.id"), nullable=False)
    panel_number = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)   # scene description
    dialogue = db.Column(db.Text, nullable=True)       # caption / speech bubble text
    image_file = db.Column(db.String(255), nullable=True)  # AI-generated panel image
    image_prompt = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    issue = db.relationship("ComicIssue", back_populates="panels")

    def __repr__(self):
        return f"<ComicPanel issue={self.issue_id} panel={self.panel_number}>"
