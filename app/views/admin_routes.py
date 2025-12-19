import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models.comic import Comic
from ..models.character import Character


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_PDF = {"pdf"}
ALLOWED_IMG = {"png", "jpg", "jpeg", "webp"}


def allowed_pdf(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PDF


def allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMG


def save_character_image(file_storage) -> str:
    """
    Save uploaded character image to:
      app/static/uploads/characters/
    Returns the stored filename to put in DB.
    """
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "characters")
    os.makedirs(upload_dir, exist_ok=True)

    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[1].lower()

    # Prevent collisions
    new_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(upload_dir, new_name)
    file_storage.save(save_path)
    return new_name


# =====================================================
# ADMIN: CREATE COMIC
# =====================================================
@admin_bp.route("/comics/new", methods=["GET", "POST"])
@login_required
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
@login_required
def admin_comics_list():
    comics = Comic.query.order_by(Comic.created_at.desc()).all()
    return render_template("admin/comics_list.html", comics=comics)


# =====================================================
# ADMIN: EDIT COMIC
# =====================================================
@admin_bp.route("/comics/<int:comic_id>/edit", methods=["GET", "POST"])
@login_required
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
                pass

        comic.pdf_file = new_filename

    db.session.commit()
    flash("Comic updated!", "success")
    return redirect(url_for("admin.admin_comics_list"))


# =====================================================
# ADMIN: DELETE COMIC (POST ONLY)
# =====================================================
@admin_bp.route("/comics/<int:comic_id>/delete", methods=["POST"])
@login_required
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
@login_required
def admin_characters_list():
    characters = Character.query.order_by(Character.created_at.desc()).all()
    return render_template("admin/characters_list.html", characters=characters)


# =====================================================
# ADMIN: CREATE CHARACTER (WITH IMAGE)
# =====================================================
@admin_bp.route("/characters/new", methods=["GET", "POST"])
@login_required
def admin_create_character():
    if request.method == "GET":
        return render_template("admin/character_new.html")

    superhero_name = request.form.get("superhero_name", "").strip()
    powers = request.form.get("powers", "").strip()
    weakness = request.form.get("weakness", "").strip()
    origins = request.form.get("origins", "").strip()
    image = request.files.get("image_file")

    if not superhero_name:
        flash("Superhero name is required.", "danger")
        return redirect(url_for("admin.admin_create_character"))

    image_filename = None
    if image and image.filename:
        if not allowed_image(image.filename):
            flash("Image must be png/jpg/jpeg/webp.", "danger")
            return redirect(url_for("admin.admin_create_character"))
        image_filename = save_character_image(image)

    character = Character(
        superhero_name=superhero_name,
        powers=powers or None,
        weakness=weakness or None,
        origins=origins or None,
        image_file=image_filename
    )
    db.session.add(character)
    db.session.commit()

    flash("Character created!", "success")
    return redirect(url_for("admin.admin_characters_list"))


# =====================================================
# ADMIN: EDIT CHARACTER (WITH IMAGE REPLACE)
# =====================================================
@admin_bp.route("/characters/<int:character_id>/edit", methods=["GET", "POST"])
@login_required
def admin_edit_character(character_id):
    character = Character.query.get_or_404(character_id)

    if request.method == "GET":
        return render_template("admin/character_edit.html", character=character)

    superhero_name = request.form.get("superhero_name", "").strip()
    powers = request.form.get("powers", "").strip()
    weakness = request.form.get("weakness", "").strip()
    origins = request.form.get("origins", "").strip()
    image = request.files.get("image_file")

    if not superhero_name:
        flash("Superhero name is required.", "danger")
        return redirect(url_for("admin.admin_edit_character", character_id=character.id))

    character.superhero_name = superhero_name
    character.powers = powers or None
    character.weakness = weakness or None
    character.origins = origins or None

    # Optional: replace image if a new one is uploaded
    if image and image.filename:
        if not allowed_image(image.filename):
            flash("Image must be png/jpg/jpeg/webp.", "danger")
            return redirect(url_for("admin.admin_edit_character", character_id=character.id))

        new_filename = save_character_image(image)

        # Optional cleanup: delete old image file
        if character.image_file and character.image_file != new_filename:
            old_path = os.path.join(
                current_app.root_path, "static", "uploads", "characters", character.image_file
            )
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
            except Exception:
                pass

        character.image_file = new_filename

    db.session.commit()
    flash("Character updated!", "success")
    return redirect(url_for("admin.admin_characters_list"))


# =====================================================
# ADMIN: DELETE CHARACTER (POST ONLY) + IMAGE CLEANUP
# =====================================================
@admin_bp.route("/characters/<int:character_id>/delete", methods=["POST"])
@login_required
def admin_delete_character(character_id):
    character = Character.query.get_or_404(character_id)

    # Optional cleanup: delete image from disk
    if character.image_file:
        img_path = os.path.join(
            current_app.root_path, "static", "uploads", "characters", character.image_file
        )
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
        except Exception:
            pass

    db.session.delete(character)
    db.session.commit()

    flash("Character deleted.", "warning")
    return redirect(url_for("admin.admin_characters_list"))
