import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models.comic import Comic

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_PDF = {"pdf"}

def allowed_pdf(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PDF

@admin_bp.route("/comics/new", methods=["GET", "POST"])
def admin_create_comic():
    if request.method == "GET":
        return render_template("admin/comic_new.html")

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    pdf = request.files.get("pdf_file")

    if not title:
        flash("Title is required.", "danger")
        return redirect(url_for("admin.admin_create_comic"))

    pdf_filename = None
    if pdf and pdf.filename:
        if not allowed_pdf(pdf.filename):
            flash("PDF file only (.pdf).", "danger")
            return redirect(url_for("admin.admin_create_comic"))

        os.makedirs(os.path.join(current_app.root_path, "static", "uploads", "pdfs"), exist_ok=True)

        pdf_filename = secure_filename(pdf.filename)
        save_path = os.path.join(current_app.root_path, "static", "uploads", "pdfs", pdf_filename)
        pdf.save(save_path)

    comic = Comic(title=title, description=description, pdf_file=pdf_filename)
    db.session.add(comic)
    db.session.commit()

    flash("Comic created!", "success")
    return redirect(url_for("comics.comic_detail", comic_id=comic.id))
