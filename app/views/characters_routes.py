from flask import Blueprint, render_template
from ..models.character import Character

characters_bp = Blueprint("characters", __name__, url_prefix="/characters")

@characters_bp.route("/")
def list_characters():
    characters = Character.query.order_by(Character.created_at.desc()).all()
    return render_template("characters/list.html", characters=characters)
