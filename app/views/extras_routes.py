import os
import uuid
from datetime import date

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models.character import Character
from ..models.fanart import FanArt
from ..services.badges import record_badge_progress

extras_bp = Blueprint("extras", __name__, url_prefix="/extras")

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

DAILY_MISSIONS = [
    "Draw a superhero who can turn into any animal!",
    "Design a villain whose power is bad breath!",
    "Create a hero team where everyone is also a chef!",
    "Draw a hero who accidentally shrinks to the size of an ant!",
    "Invent a superpower that involves spaghetti!",
    "Design a hero whose costume is made entirely of bubble wrap!",
    "Create a villain who only wants to steal everyone's homework!",
    "Draw a superhero whose sidekick is a super-smart dog!",
    "Design a power that lets you speak every language including cat!",
    "Create a hero who can only use their powers when they sneeze!",
    "Draw a villain who accidentally becomes good by eating too much pizza!",
    "Design a hero team that only accepts members who can juggle!",
    "Create a super move that involves time-traveling to ancient Egypt!",
    "Draw a hero who turns invisible but only when scared!",
    "Invent a gadget for heroes who are afraid of the dark!",
    "Design a villain base that's inside a giant rubber duck!",
    "Create a hero whose weakness is tickling!",
    "Draw a superhero who loves to do the moonwalk while fighting!",
    "Design a hero with the power to make everyone break into dance!",
    "Create a story where the villain and hero have to team up!",
    "Draw a hero who can talk to plants — but the plants are grumpy!",
    "Invent a superpower that only works on Tuesdays!",
    "Design a hero whose jet pack runs on chocolate milk!",
    "Create a villain who just really wants a puppy!",
    "Draw a superhero who fights crime using a giant spoon!",
    "Design the ultimate hero snack that gives them extra power!",
    "Create a hero who can run fast but only backwards!",
    "Draw a villain who turns good the moment someone shares their lunch!",
    "Invent a hero vehicle that's actually a giant sneaker!",
    "Create a superhero team where each member is scared of something silly!",
    "Draw a hero who can shoot rainbows from their hands!",
]

QUIZ_QUESTIONS = [
    {
        "question": "Your city is flooded! What's your first move?",
        "answers": [
            {"text": "Fly above and rescue people one by one", "power": "flight"},
            {"text": "Freeze the flood water instantly", "power": "ice"},
            {"text": "Teleport everyone to safety", "power": "teleportation"},
            {"text": "Stretch my arms to make a giant bridge", "power": "elasticity"},
        ]
    },
    {
        "question": "A giant robot is attacking! How do you stop it?",
        "answers": [
            {"text": "Punch it with super strength!", "power": "strength"},
            {"text": "Shoot lightning bolts at its circuits", "power": "lightning"},
            {"text": "Shrink it down to pocket size", "power": "size-control"},
            {"text": "Use mind powers to make it shut down", "power": "telepathy"},
        ]
    },
    {
        "question": "You need to catch a villain running away. You...",
        "answers": [
            {"text": "Run faster than a cheetah", "power": "speed"},
            {"text": "Create a wall of ice in front of them", "power": "ice"},
            {"text": "Fly over and block their path", "power": "flight"},
            {"text": "Teleport right in front of them", "power": "teleportation"},
        ]
    },
    {
        "question": "What would your superhero HQ look like?",
        "answers": [
            {"text": "A volcano fortress", "power": "fire"},
            {"text": "A cloud castle in the sky", "power": "flight"},
            {"text": "An underwater base", "power": "water"},
            {"text": "A secret lab full of gadgets", "power": "tech"},
        ]
    },
    {
        "question": "Your favorite kind of mission is...",
        "answers": [
            {"text": "Rescuing people from danger", "power": "strength"},
            {"text": "Outsmarting the villain with brains", "power": "telepathy"},
            {"text": "Going undercover in disguise", "power": "shape-shifting"},
            {"text": "Racing against time to defuse a trap", "power": "speed"},
        ]
    },
]

POWER_RESULTS = {
    "flight": {
        "name": "Super Flight",
        "emoji": "🦅",
        "description": "You soar above it all! Speed, freedom, and a bird's-eye view make you the ultimate aerial hero.",
        "color": "blue",
    },
    "ice": {
        "name": "Ice Control",
        "emoji": "❄️",
        "description": "Chill out! You freeze villains in their tracks and build incredible ice structures.",
        "color": "blue",
    },
    "teleportation": {
        "name": "Teleportation",
        "emoji": "⚡",
        "description": "Here, there, everywhere! You vanish and reappear faster than anyone can react.",
        "color": "purple",
    },
    "elasticity": {
        "name": "Super Elasticity",
        "emoji": "🌀",
        "description": "You stretch, bounce, and squish into any shape. Villains never know what hit them!",
        "color": "green",
    },
    "strength": {
        "name": "Super Strength",
        "emoji": "💪",
        "description": "You're the strongest hero around! Nothing can stop those mighty muscles.",
        "color": "red",
    },
    "lightning": {
        "name": "Lightning Control",
        "emoji": "⚡",
        "description": "ZAP! You command lightning and electricity to stop evil in a flash.",
        "color": "yellow",
    },
    "size-control": {
        "name": "Size Control",
        "emoji": "🔬",
        "description": "Tiny or giant — you pick! Shrink to sneak in or grow huge to stop any threat.",
        "color": "green",
    },
    "telepathy": {
        "name": "Telepathy",
        "emoji": "🧠",
        "description": "You read minds and control thoughts. The smartest power of all!",
        "color": "purple",
    },
    "speed": {
        "name": "Super Speed",
        "emoji": "💨",
        "description": "ZOOM! You're faster than lightning. Bad guys never see you coming.",
        "color": "red",
    },
    "fire": {
        "name": "Fire Control",
        "emoji": "🔥",
        "description": "You command flames! Hot, bright, and blazing — you're the fire hero.",
        "color": "red",
    },
    "water": {
        "name": "Water Control",
        "emoji": "🌊",
        "description": "Waves, whirlpools, and water blasts — you rule the seas and rivers!",
        "color": "blue",
    },
    "tech": {
        "name": "Tech Genius",
        "emoji": "🤖",
        "description": "Your gadgets and inventions make you the smartest hero in the universe!",
        "color": "yellow",
    },
    "shape-shifting": {
        "name": "Shape Shifting",
        "emoji": "🦎",
        "description": "You can become anyone or anything! Masters of disguise and surprise.",
        "color": "green",
    },
}


def _get_today_mission() -> str:
    day_of_year = date.today().timetuple().tm_yday
    return DAILY_MISSIONS[day_of_year % len(DAILY_MISSIONS)]


def _allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@extras_bp.route("/mission")
def daily_mission():
    mission = _get_today_mission()
    today = date.today()
    if current_user.is_authenticated:
        last = session.get("last_mission_date")
        if str(today) != last:
            session["last_mission_date"] = str(today)
            record_badge_progress(current_user, "mission-ace")
    return render_template("extras/mission.html", mission=mission, today=today)


@extras_bp.route("/quiz", methods=["GET", "POST"])
def superpower_quiz():
    if request.method == "GET":
        return render_template("extras/quiz.html", questions=QUIZ_QUESTIONS, result=None)

    answers = []
    for i, q in enumerate(QUIZ_QUESTIONS):
        answer_idx = request.form.get(f"q{i}", type=int)
        if answer_idx is not None and 0 <= answer_idx < len(q["answers"]):
            answers.append(q["answers"][answer_idx]["power"])

    if not answers:
        flash("Please answer at least one question!", "warning")
        return redirect(url_for("extras.superpower_quiz"))

    # Tally power votes
    power_tally = {}
    for power in answers:
        power_tally[power] = power_tally.get(power, 0) + 1

    top_power = max(power_tally, key=power_tally.get)
    result = POWER_RESULTS.get(top_power, POWER_RESULTS["strength"])

    if current_user.is_authenticated:
        record_badge_progress(current_user, "quiz-master")

    return render_template("extras/quiz.html", questions=QUIZ_QUESTIONS, result=result)


@extras_bp.route("/timeline")
def timeline():
    return render_template("extras/timeline.html")


@extras_bp.route("/fanart", methods=["GET", "POST"])
def fanart_wall():
    if request.method == "POST":
        title = " ".join(request.form.get("title", "").split())
        artist_name = " ".join(request.form.get("artist_name", "").split())
        description = " ".join(request.form.get("description", "").split())
        image_file = request.files.get("image")

        if not title or not artist_name:
            flash("Title and artist name are required!", "danger")
            return redirect(url_for("extras.fanart_wall"))

        if not image_file or not image_file.filename:
            flash("Please upload an image file!", "danger")
            return redirect(url_for("extras.fanart_wall"))

        if not _allowed_image(image_file.filename):
            flash("Only image files allowed (PNG, JPG, GIF, WebP).", "danger")
            return redirect(url_for("extras.fanart_wall"))

        upload_dir = os.path.join(current_app.root_path, "static", "uploads", "fanart")
        os.makedirs(upload_dir, exist_ok=True)
        ext = image_file.filename.rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        image_file.save(os.path.join(upload_dir, filename))

        art = FanArt(
            title=title,
            artist_name=artist_name,
            description=description or None,
            image_file=filename,
            user_id=current_user.id if current_user.is_authenticated else None,
        )
        db.session.add(art)
        db.session.commit()

        if current_user.is_authenticated:
            record_badge_progress(current_user, "fan-artist")

        flash("Fan art uploaded! Amazing work!", "success")
        return redirect(url_for("extras.fanart_wall"))

    artworks = FanArt.query.order_by(FanArt.created_at.desc()).all()
    return render_template("extras/fanart.html", artworks=artworks)
