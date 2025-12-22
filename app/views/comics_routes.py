from flask import Blueprint, render_template, abort, current_app, send_from_directory, request, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import safe_join
from ..extensions import db
from ..models.comic import Comic
from ..models.comment import Comment
import os

comics_bp = Blueprint("comics", __name__)


# =====================================================
# LIST ALL COMICS
# =====================================================
@comics_bp.route("/")
def list_comics():
    comics = Comic.query.order_by(Comic.created_at.desc()).all()
    return render_template("comics/list.html", comics=comics)


# =====================================================
# COMIC DETAIL (INFO PAGE)
# =====================================================
@comics_bp.route("/<int:comic_id>")
def comic_detail(comic_id):
    comic = Comic.query.get_or_404(comic_id)
    comments = Comment.query.filter_by(comic_id=comic.id).order_by(Comment.created_at.desc()).all()
    return render_template("comics/detail.html", comic=comic, comments=comments)


# =====================================================
# COMIC READER
# =====================================================
@comics_bp.route("/read/<int:comic_id>")
def comic_reader(comic_id):
    comic = Comic.query.get_or_404(comic_id)

    # DB stores only the filename (e.g. "issue_1.pdf")
    if not comic.pdf_file or not comic.pdf_file.lower().endswith(".pdf"):
        abort(404)

    return render_template(
        "comics/reader.html",
        comic=comic,
        pdf_file=comic.pdf_file
    )


# =====================================================
# SECURE PDF SERVING (USED BY PDF.js)
# =====================================================
@comics_bp.route("/pdf/<path:filename>")
def serve_pdf(filename):
    # Only allow PDFs
    if not filename.lower().endswith(".pdf"):
        abort(404)

    # Flask knows exactly where /static lives
    # This resolves to: app/static
    static_root = current_app.static_folder

    # Your PDFs live here: app/static/uploads/pdfs
    pdf_dir = os.path.join(static_root, "uploads", "pdfs")

    # Resolve the final path safely
    full_path = safe_join(pdf_dir, filename)
    if not full_path or not os.path.isfile(full_path):
        abort(404)

    return send_from_directory(pdf_dir, filename)


# =====================================================
# COMMENT CREATION
# =====================================================
@comics_bp.route("/<int:comic_id>/comments", methods=["POST"])
@login_required
def add_comment(comic_id):
    comic = Comic.query.get_or_404(comic_id)
    body = request.form.get("comment", "").strip()

    if not body:
        flash("Please enter a comment before posting.", "warning")
        return redirect(url_for("comics.comic_detail", comic_id=comic.id))

    comment = Comment(body=body, comic_id=comic.id, user_id=current_user.id)
    db.session.add(comment)
    db.session.commit()

    flash("Comment added!", "success")
    return redirect(url_for("comics.comic_detail", comic_id=comic.id))
