from flask import Blueprint, render_template, abort, current_app, send_from_directory
from werkzeug.utils import safe_join
from ..models.comic import Comic
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
    return render_template("comics/detail.html", comic=comic)


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
