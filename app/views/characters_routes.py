import base64
import json
import os
import uuid
import urllib.error
import urllib.request

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from ..extensions import db
from ..models.character import Character

characters_bp = Blueprint("characters", __name__, url_prefix="/characters")

STYLE_PROMPT = """
Overall Comic Style:
- Kid-friendly cartoon comic
- Thick black outlines
- Simple, rounded shapes
- Slightly exaggerated proportions (big heads, expressive eyes)
- Easy-to-read layouts
- Clear action and emotions
- Playful, energetic, hand-drawn feel

Tone:
- Fun and adventurous
- Curious and exciting, never scary
- Mysterious but friendly
- Heroic in a way kids immediately understand

Motion & Effects:
- Squiggly energy lines
- Floating objects when powers activate
- Big, playful sound effects
- Action feels bouncy and dynamic, not violent
""".strip()

MIN_HERO_AGE = 4
MAX_HERO_AGE = 16


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def normalize_color(value: str) -> str:
    return normalize_text(value).lower()


def build_image_prompt(hero_data: dict) -> str:
    prompt_lines = [
        "Create a single kid superhero character portrait.",
        "The hero should look like a child and feel friendly, brave, and fun.",
        f"Superhero name: {hero_data['superhero_name']}",
        f"Age: {hero_data['age']} (child hero)",
        f"Costume color: {hero_data['costume_color']}",
        f"Boots color: {hero_data['boots_color']}",
        f"Gloves color: {hero_data['gloves_color']}",
        f"Chest symbol: {hero_data['chest_symbol']}",
        f"Eye mask color: {hero_data['eye_mask_color']}",
        f"Cape color: {hero_data['cape_color']}",
        f"Hair color: {hero_data['hair_color']}",
        f"Powers: {hero_data['powers']}",
        f"Weakness: {hero_data['weakness']}",
        f"Origin story: {hero_data['origin_story']}",
        "",
        STYLE_PROMPT,
    ]
    return "\n".join(prompt_lines)


def save_generated_image_bytes(image_bytes: bytes) -> str:
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "characters")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    save_path = os.path.join(upload_dir, filename)

    with open(save_path, "wb") as file_obj:
        file_obj.write(image_bytes)

    return filename


def generate_hero_image(prompt: str) -> str | None:
    api_key = current_app.config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    payload = json.dumps(
        {
            "model": "gpt-image-1",
            "prompt": prompt,
            "size": "1024x1024",
        }
    ).encode("utf-8")

    request_obj = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request_obj) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        current_app.logger.error("OpenAI image generation failed: %s", error_body)
        return None

    image_data = response_body["data"][0]
    if "b64_json" in image_data:
        image_bytes = base64.b64decode(image_data["b64_json"])
    elif "url" in image_data:
        with urllib.request.urlopen(image_data["url"]) as image_response:
            image_bytes = image_response.read()
    else:
        current_app.logger.error("OpenAI image response missing image data.")
        return None
    return save_generated_image_bytes(image_bytes)


def generate_origin_story(origin_prompt: str, hero_name: str) -> str | None:
    api_key = current_app.config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    prompt = (
        "Rewrite the hero origin into a more detailed, thrilling, kid-friendly story. "
        "Keep it uplifting, adventurous, and suitable for ages 6-12. "
        "Use 3-5 sentences and mention the hero's name once. "
        f"Hero name: {hero_name}. "
        f"Origin: {origin_prompt}"
    )

    payload = json.dumps(
        {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "max_tokens": 200,
        }
    ).encode("utf-8")

    request_obj = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request_obj) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        current_app.logger.error("OpenAI origin story failed: %s", error_body)
        return None

    return response_body["choices"][0]["message"]["content"].strip()


@characters_bp.route("/")
def list_characters():
    characters = Character.query.order_by(Character.created_at.desc()).all()
    return render_template("characters/list.html", characters=characters)


@characters_bp.route("/create", methods=["GET", "POST"])
def create_character():
    if request.method == "GET":
        return render_template("characters/create.html")

    superhero_name = normalize_text(request.form.get("superhero_name", ""))
    costume_color = normalize_color(request.form.get("costume_color", ""))
    boots_color = normalize_color(request.form.get("boots_color", ""))
    gloves_color = normalize_color(request.form.get("gloves_color", ""))
    chest_symbol = normalize_text(request.form.get("chest_symbol", ""))
    eye_mask_color = normalize_color(request.form.get("eye_mask_color", ""))
    cape_color = normalize_color(request.form.get("cape_color", ""))
    hair_color = normalize_color(request.form.get("hair_color", ""))
    powers = normalize_text(request.form.get("powers", ""))
    weakness = normalize_text(request.form.get("weakness", ""))
    hero_origin = normalize_text(request.form.get("hero_origin", ""))
    age_raw = normalize_text(request.form.get("age", ""))

    required_fields = {
        "Superhero name": superhero_name,
        "Costume color": costume_color,
        "Boots color": boots_color,
        "Gloves color": gloves_color,
        "Hero chest symbol": chest_symbol,
        "Eye mask color": eye_mask_color,
        "Cape color": cape_color,
        "Hair color": hair_color,
        "Powers": powers,
        "Weakness": weakness,
        "Hero origin": hero_origin,
        "Age": age_raw,
    }

    missing_fields = [label for label, value in required_fields.items() if not value]
    if missing_fields:
        flash(
            f"Please fill out every field: {', '.join(missing_fields)}.",
            "danger",
        )
        return redirect(url_for("characters.create_character"))

    try:
        age = int(age_raw)
    except ValueError:
        flash("Age must be a number.", "danger")
        return redirect(url_for("characters.create_character"))

    if age < MIN_HERO_AGE or age > MAX_HERO_AGE:
        flash(
            f"Heroes should be between {MIN_HERO_AGE} and {MAX_HERO_AGE} years old.",
            "danger",
        )
        return redirect(url_for("characters.create_character"))

    origin_story = generate_origin_story(hero_origin, superhero_name) or hero_origin

    hero_data = {
        "superhero_name": superhero_name,
        "costume_color": costume_color,
        "boots_color": boots_color,
        "gloves_color": gloves_color,
        "chest_symbol": chest_symbol,
        "eye_mask_color": eye_mask_color,
        "cape_color": cape_color,
        "hair_color": hair_color,
        "powers": powers,
        "weakness": weakness,
        "age": age,
        "origin_story": origin_story,
    }

    prompt = build_image_prompt(hero_data)
    image_filename = None
    try:
        image_filename = generate_hero_image(prompt)
    except Exception:
        current_app.logger.exception("Failed to generate hero image.")
        image_filename = None

    character = Character(
        superhero_name=superhero_name,
        powers=powers,
        weakness=weakness,
        origins=origin_story,
        image_prompt=prompt,
        costume_color=costume_color,
        boots_color=boots_color,
        gloves_color=gloves_color,
        chest_symbol=chest_symbol,
        eye_mask_color=eye_mask_color,
        cape_color=cape_color,
        age=age,
        hair_color=hair_color,
        image_file=image_filename,
    )

    db.session.add(character)
    db.session.commit()

    if image_filename:
        flash("Hero created! Your new hero just landed in Isma Verse.", "success")
    else:
        flash(
            "Hero created! Image generation is queued once the OpenAI key is configured.",
            "warning",
        )

    return redirect(url_for("characters.list_characters"))
