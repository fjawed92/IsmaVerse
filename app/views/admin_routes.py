import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models.comic import Comic
from ..models.character import Character

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

        upload_dir = os.path.join(current_app.root_path, "static", "uploads", "pdfs")
        os.makedirs(upload_dir, exist_ok=True)

        pdf_filename = secure_filename(pdf.filename)
        save_path = os.path.join(upload_dir, pdf_filename)
        pdf.save(save_path)

    comic = Comic(title=title, description=description, pdf_file=pdf_filename)
    db.session.add(comic)
    db.session.commit()

    flash("Comic created!", "success")
    return redirect(url_for("comics.comic_detail", comic_id=comic.id))


# =====================================================
# ADMIN: LIST ALL COMICS
# =====================================================
@admin_bp.route("/comics", methods=["GET"])
def admin_comics_list():
    comics = Comic.query.order_by(Comic.created_at.desc()).all()
    return render_template("admin/comics_list.html", comics=comics)


# =====================================================
# ADMIN: EDIT COMIC
# =====================================================
@admin_bp.route("/comics/<int:comic_id>/edit", methods=["GET", "POST"])
def admin_edit_comic(comic_id):
    comic = Comic.query.get_or_404(comic_id)

    if request.method == "GET":
        return render_template("admin/comic_edit.html", comic=comic)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    pdf = request.files.get("pdf_file")

    if not title:
        flash("Title is required.", "danger")
        return redirect(url_for("admin.admin_edit_comic", comic_id=comic.id))

    comic.title = title
    comic.description = description

    # Optional: replace PDF if a new one is uploaded
    if pdf and pdf.filename:
        if not allowed_pdf(pdf.filename):
            flash("PDF file only (.pdf).", "danger")
            return redirect(url_for("admin.admin_edit_comic", comic_id=comic.id))

        upload_dir = os.path.join(current_app.root_path, "static", "uploads", "pdfs")
        os.makedirs(upload_dir, exist_ok=True)

        new_filename = secure_filename(pdf.filename)
        save_path = os.path.join(upload_dir, new_filename)
        pdf.save(save_path)

        # Optional cleanup: delete old file if it's different
        if comic.pdf_file and comic.pdf_file != new_filename:
            old_path = os.path.join(upload_dir, comic.pdf_file)
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
            except Exception:
                # Don't fail the request if delete fails
                pass

        comic.pdf_file = new_filename

    db.session.commit()
    flash("Comic updated!", "success")
    return redirect(url_for("admin.admin_comics_list"))


# =====================================================
# ADMIN: DELETE COMIC (POST ONLY)
# =====================================================
@admin_bp.route("/comics/<int:comic_id>/delete", methods=["POST"])
def admin_delete_comic(comic_id):
    comic = Comic.query.get_or_404(comic_id)

    # Optional cleanup: remove PDF file
    if comic.pdf_file:
        upload_dir = os.path.join(current_app.root_path, "static", "uploads", "pdfs")
        file_path = os.path.join(upload_dir, comic.pdf_file)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

    db.session.delete(comic)
    db.session.commit()

    flash("Comic deleted.", "warning")
    return redirect(url_for("admin.admin_comics_list"))

# =====================================================
# ADMIN: LIST CHARACTERS
# =====================================================
@admin_bp.route("/characters", methods=["GET"])
def admin_characters_list():
    characters = Character.query.order_by(Character.created_at.desc()).all()
    return render_template("admin/characters_list.html", characters=characters)


# =====================================================
# ADMIN: CREATE CHARACTER
# =====================================================
@admin_bp.route("/characters/new", methods=["GET", "POST"])
def admin_create_character():
    if request.method == "GET":
        return render_template("admin/character_new.html")

    superhero_name = request.form.get("superhero_name", "").strip()
    powers = request.form.get("powers", "").strip()
    weakness = request.form.get("weakness", "").strip()
    origins = request.form.get("origins", "").strip()

    if not superhero_name:
        flash("Superhero name is required.", "danger")
        return redirect(url_for("admin.admin_create_character"))

    character = Character(
        superhero_name=superhero_name,
        powers=powers or None,
        weakness=weakness or None,
        origins=origins or None,
    )
    db.session.add(character)
    db.session.commit()

    flash("Character created!", "success")
    return redirect(url_for("admin.admin_characters_list"))


# =====================================================
# ADMIN: EDIT CHARACTER
# =====================================================
@admin_bp.route("/characters/<int:character_id>/edit", methods=["GET", "POST"])
def admin_edit_character(character_id):
    character = Character.query.get_or_404(character_id)

    if request.method == "GET":
        return render_template("admin/character_edit.html", character=character)

    superhero_name = request.form.get("superhero_name", "").strip()
    powers = request.form.get("powers", "").strip()
    weakness = request.form.get("weakness", "").strip()
    origins = request.form.get("origins", "").strip()

    if not superhero_name:
        flash("Superhero name is required.", "danger")
        return redirect(url_for("admin.admin_edit_character", character_id=character.id))

    character.superhero_name = superhero_name
    character.powers = powers or None
    character.weakness = weakness or None
    character.origins = origins or None

    db.session.commit()
    flash("Character updated!", "success")
    return redirect(url_for("admin.admin_characters_list"))


# =====================================================
# ADMIN: DELETE CHARACTER (POST ONLY)
# =====================================================
@admin_bp.route("/characters/<int:character_id>/delete", methods=["POST"])
def admin_delete_character(character_id):
    character = Character.query.get_or_404(character_id)

    db.session.delete(character)
    db.session.commit()

    flash("Character deleted.", "warning")
    return redirect(url_for("admin.admin_characters_list"))
