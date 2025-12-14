from flask import Blueprint, render_template
from ..models.comic import Comic

comics_bp = Blueprint("comics", __name__)

@comics_bp.route("/")
def list_comics():
    comics = Comic.query.order_by(Comic.created_at.desc()).all()
    return render_template("comics/list.html", comics=comics)

@comics_bp.route("/<int:comic_id>")
def comic_detail(comic_id):
    comic = Comic.query.get_or_404(comic_id)
    return render_template("comics/detail.html", comic=comic)
