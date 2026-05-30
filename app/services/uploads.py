import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename

# Image types we accept for user uploads.
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _extension(filename):
    """Return the lowercased extension (without the dot), or ''."""
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def is_allowed_image(filename):
    """True if the filename has a supported image extension."""
    return _extension(filename) in ALLOWED_IMAGE_EXTENSIONS


def save_uploaded_image(file_storage, folder, prefix):
    """Validate and save an uploaded image file.

    Returns the saved filename on success, or None if there is no file,
    the extension is not allowed, or the file is not a valid image.
    """
    if not file_storage or not file_storage.filename:
        return None

    ext = _extension(secure_filename(file_storage.filename))
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        current_app.logger.warning(f"Rejected upload with extension: {ext!r}")
        return None

    os.makedirs(folder, exist_ok=True)
    filename = f"{prefix}_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(folder, filename)
    file_storage.save(filepath)

    # Verify the saved file really is an image; remove it if not.
    try:
        from PIL import Image
        with Image.open(filepath) as img:
            img.verify()
    except Exception as e:
        current_app.logger.warning(f"Uploaded file is not a valid image: {e}")
        try:
            os.remove(filepath)
        except OSError:
            pass
        return None

    return filename


def delete_image(folder, filename):
    """Delete a previously saved image file, ignoring errors."""
    if not filename:
        return
    try:
        os.remove(os.path.join(folder, filename))
    except OSError:
        pass
