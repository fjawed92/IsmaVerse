import base64
import json
import os
import uuid
import urllib.error
import urllib.request

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..extensions import db
from ..models.villain import Villain
from ..services.badges import record_badge_progress

villains_bp = Blueprint("villains", __name__, url_prefix="/villains")

VILLAIN_STYLE_PROMPT = """
Overall Comic Style:
- Kid-friendly cartoon comic villain
- Thick black outlines
- Sinister but NOT scary — more goofy-evil like a cartoon bad guy
- Slightly exaggerated proportions
- Playful, energetic, hand-drawn feel

Tone:
- Mischievous and silly
- Dramatic villain poses
- Comic-book evil — think Joker Jr., not nightmare fuel
- Colorful costumes with lightning bolts, skulls, or weird gadgets
""".strip()


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def normalize_color(value: str) -> str:
    return normalize_text(value).lower()


def build_villain_image_prompt(villain_data: dict) -> str:
    lines = [
        "Create a single kid-friendly cartoon VILLAIN character portrait.",
        "The villain should look goofy-evil, like a cartoon bad guy — fun, not scary.",
        f"Villain name: {villain_data['villain_name']}",
        f"Age: {villain_data.get('age', 'unknown')}",
        f"Costume color: {villain_data['costume_color']}",
        f"Hair color: {villain_data.get('hair_color', 'black')}",
        f"Evil powers: {villain_data['powers']}",
        f"Evil plan: {villain_data.get('evil_plan', 'world domination')}",
        f"Lair location: {villain_data.get('lair_location', 'secret underground lair')}",
        "",
        VILLAIN_STYLE_PROMPT,
    ]
    return "\n".join(lines)


def save_generated_image_bytes(image_bytes: bytes) -> str:
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "villains")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    save_path = os.path.join(upload_dir, filename)
    with open(save_path, "wb") as f:
        f.write(image_bytes)
    return filename


def generate_villain_image(prompt: str) -> str | None:
    api_key = current_app.config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    payload = json.dumps({
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": "1024x1024",
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        current_app.logger.error("OpenAI villain image failed: %s", exc.read().decode())
        return None

    image_data = body["data"][0]
    if "b64_json" in image_data:
        image_bytes = base64.b64decode(image_data["b64_json"])
    elif "url" in image_data:
        with urllib.request.urlopen(image_data["url"]) as img_resp:
            image_bytes = img_resp.read()
    else:
        return None
    return save_generated_image_bytes(image_bytes)


@villains_bp.route("/")
def list_villains():
    villains = Villain.query.order_by(Villain.created_at.desc()).all()
    return render_template("villains/list.html", villains=villains)


@villains_bp.route("/create", methods=["GET", "POST"])
def create_villain():
    if request.method == "GET":
        return render_template("villains/create.html")

    villain_name = normalize_text(request.form.get("villain_name", ""))
    costume_color = normalize_color(request.form.get("costume_color", ""))
    powers = normalize_text(request.form.get("powers", ""))
    weakness = normalize_text(request.form.get("weakness", ""))
    evil_plan = normalize_text(request.form.get("evil_plan", ""))
    lair_location = normalize_text(request.form.get("lair_location", ""))
    hair_color = normalize_color(request.form.get("hair_color", ""))
    age_raw = normalize_text(request.form.get("age", ""))

    required_fields = {
        "Villain name": villain_name,
        "Costume color": costume_color,
        "Evil powers": powers,
        "Weakness": weakness,
        "Evil plan": evil_plan,
    }

    missing = [label for label, value in required_fields.items() if not value]
    if missing:
        flash(f"Please fill out: {', '.join(missing)}.", "danger")
        return redirect(url_for("villains.create_villain"))

    age = None
    if age_raw:
        try:
            age = int(age_raw)
        except ValueError:
            pass

    villain_data = {
        "villain_name": villain_name,
        "costume_color": costume_color,
        "powers": powers,
        "weakness": weakness,
        "evil_plan": evil_plan,
        "lair_location": lair_location,
        "hair_color": hair_color,
        "age": age,
    }

    prompt = build_villain_image_prompt(villain_data)
    image_filename = None
    try:
        image_filename = generate_villain_image(prompt)
    except Exception:
        current_app.logger.exception("Failed to generate villain image.")

    villain = Villain(
        villain_name=villain_name,
        powers=powers,
        weakness=weakness,
        evil_plan=evil_plan,
        lair_location=lair_location,
        costume_color=costume_color,
        hair_color=hair_color,
        age=age,
        image_prompt=prompt,
        image_file=image_filename,
    )

    db.session.add(villain)
    db.session.commit()

    if current_user.is_authenticated:
        record_badge_progress(current_user, "villain-maker")

    if image_filename:
        flash("Villain unleashed! They've arrived in IsmaVerse. Watch out, heroes!", "success")
    else:
        flash("Villain created! Image generation needs OpenAI key to be configured.", "warning")

    return redirect(url_for("villains.list_villains"))
