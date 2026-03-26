import base64
import json
import os
import random as _random
import uuid
import urllib.error
import urllib.request

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.character import Character
from ..models.hero_reaction import HeroReaction, REACTION_TYPES
from ..models.hero_comment import HeroComment
from ..services.badges import record_badge_progress

characters_bp = Blueprint("characters", __name__, url_prefix="/characters")

STYLE_PROMPT = """
ART STYLE:
- Premium animated comic book illustration — think DC Animated Series meets modern Marvel comics
- Clean, bold ink outlines with confident line weight variation (thicker on outer edges, thinner inside)
- Vivid, highly saturated colours with strong contrast — this image should POP off the page
- Dramatic cel-shading with clear highlight and shadow areas
- The finished image should look like professional, print-quality comic book art

COMPOSITION:
- FULL BODY illustration — show the entire hero from head to boots in a dynamic three-quarter angle
- Heroic power stance: legs shoulder-width apart, chest forward, one fist raised or energy crackling from hands
- If the hero has a cape, it billows dramatically behind them as if caught by the wind
- Background: bold radial speed lines (like a classic comic splash page) on a vibrant gradient — no complex scenes
- Dramatic rim/back-lighting that creates a glowing aura silhouette around the hero

POWER VISUALISATION:
- The hero's powers MUST be visually shown in the image
- Energy powers → crackling electricity or light around the fists/body
- Flight powers → wind streaks and upward motion blur
- Strength powers → glowing muscles, cracked ground beneath feet
- Animal powers → ghostly animal silhouette behind hero
- Make the power effect vibrant and unmistakable

TONE:
- Kid-friendly and age-appropriate — heroic but never scary or violent
- Determined, confident expression on the hero's face (eyes visible if mask allows)
- Fun, exciting, adventurous energy — this kid is AWESOME and they know it
- Proportions can be slightly stylised/heroic but still clearly child-aged
""".strip()


def build_image_prompt(hero_data: dict) -> str:
    powers_str = hero_data["powers"]
    name = hero_data["superhero_name"]
    age = hero_data["age"]
    gender = hero_data.get("gender", "male")
    gender_label = "boy" if gender == "male" else "girl"

    prompt_lines = [
        f"SUPERHERO CHARACTER ILLUSTRATION: {name}",
        "",
        "=== CHARACTER DETAILS ===",
        f"Name: {name}",
        f"Gender: {gender} ({gender_label})",
        f"Age: {age} years old — this is a CHILD superhero. They look young, brave, and full of energy. Draw them clearly as a {gender_label}.",
        "",
        "=== COSTUME (render every detail accurately) ===",
        f"Main costume colour: {hero_data['costume_color']} — the dominant colour of their suit",
        f"Boots: {hero_data['boots_color']} boots, knee-high or ankle-high",
        f"Gloves: {hero_data['gloves_color']} gloves or gauntlets",
        f"Chest emblem: A LARGE, BOLD '{hero_data['chest_symbol']}' symbol prominently displayed on the chest — make it iconic and clearly visible",
        f"Eye mask: {hero_data['eye_mask_color']} mask across the eyes",
        f"Cape: {hero_data['cape_color']} cape — billowing dramatically, adds to the heroic silhouette",
        f"Hair: {hero_data['hair_color']} hair",
        "",
        "=== POWERS (MUST be visually shown in the image) ===",
        f"{powers_str}",
        "",
        "=== ORIGIN / PERSONALITY ===",
        f"{hero_data['origin_story'][:200]}",
        "",
        "=== STYLE REQUIREMENTS ===",
        STYLE_PROMPT,
    ]
    return "\n".join(prompt_lines)

MIN_HERO_AGE = 4
MAX_HERO_AGE = 16


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def normalize_color(value: str) -> str:
    return normalize_text(value).lower()




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
    if current_user.is_authenticated:
        record_badge_progress(current_user, "character-explorer")
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
    gender = request.form.get("gender", "male")
    if gender not in ("male", "female"):
        gender = "male"

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
        "gender": gender,
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
        gender=gender,
        image_file=image_filename,
    )

    db.session.add(character)
    db.session.commit()

    if current_user.is_authenticated:
        record_badge_progress(current_user, "hero-maker")
        record_badge_progress(current_user, "power-up")

    if image_filename:
        flash("Hero created! Your new hero just landed in Isma Verse.", "success")
    else:
        flash(
            "Hero created! Image generation is queued once the OpenAI key is configured.",
            "warning",
        )

    return redirect(url_for("characters.list_characters"))


@characters_bp.route("/<int:character_id>")
def character_detail(character_id):
    character = Character.query.get_or_404(character_id)
    all_characters = Character.query.all()

    # Session key for anonymous reactions
    if "react_session" not in session:
        session["react_session"] = uuid.uuid4().hex
    sess_key = session["react_session"]

    # Which reactions has this session already sent for this character?
    already_reacted = {
        r.reaction_type
        for r in HeroReaction.query.filter_by(character_id=character_id, session_key=sess_key).all()
    }

    return render_template(
        "characters/detail.html",
        character=character,
        all_characters=all_characters,
        reaction_types=REACTION_TYPES,
        already_reacted=already_reacted,
    )


@characters_bp.route("/<int:character_id>/react", methods=["POST"])
def react_to_hero(character_id):
    character = Character.query.get_or_404(character_id)
    reaction_type = request.form.get("reaction_type", "")

    if reaction_type not in REACTION_TYPES:
        flash("Invalid reaction.", "danger")
        return redirect(url_for("characters.character_detail", character_id=character_id))

    if "react_session" not in session:
        session["react_session"] = uuid.uuid4().hex
    sess_key = session["react_session"]

    existing = HeroReaction.query.filter_by(
        character_id=character_id,
        session_key=sess_key,
        reaction_type=reaction_type,
    ).first()

    if existing:
        flash("Already reacted with that one! Try another.", "info")
        return redirect(url_for("characters.character_detail", character_id=character_id))

    reaction = HeroReaction(
        character_id=character_id,
        reaction_type=reaction_type,
        session_key=sess_key,
        user_id=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(reaction)
    db.session.commit()

    if current_user.is_authenticated:
        total_reacts = HeroReaction.query.filter_by(user_id=current_user.id).count()
        if total_reacts >= 5:
            record_badge_progress(current_user, "reactor", increment=0)
        record_badge_progress(current_user, "reactor")

    flash(f"{reaction_type.upper()}! Reaction added!", "success")
    return redirect(url_for("characters.character_detail", character_id=character_id))


@characters_bp.route("/<int:character_id>/comment", methods=["POST"])
@login_required
def comment_on_hero(character_id):
    character = Character.query.get_or_404(character_id)
    body = " ".join(request.form.get("body", "").split())

    if not body:
        flash("Comment cannot be empty!", "danger")
        return redirect(url_for("characters.character_detail", character_id=character_id))

    if len(body) > 500:
        flash("Comment is too long (max 500 characters).", "danger")
        return redirect(url_for("characters.character_detail", character_id=character_id))

    comment = HeroComment(
        character_id=character_id,
        user_id=current_user.id,
        body=body,
    )
    db.session.add(comment)
    db.session.commit()

    record_badge_progress(current_user, "commentator")

    flash("Comment posted!", "success")
    return redirect(url_for("characters.character_detail", character_id=character_id))


@characters_bp.route("/random")
def random_character():
    characters = Character.query.all()
    if not characters:
        flash("No heroes yet! Create one first.", "warning")
        return redirect(url_for("characters.list_characters"))
    picked = _random.choice(characters)
    return redirect(url_for("characters.character_detail", character_id=picked.id))
