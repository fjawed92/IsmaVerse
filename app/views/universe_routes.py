"""
Comic Universe Routes
======================
/universe/                     - Universe hub (all story arcs)
/universe/arc/new              - Launch a new story arc (choose heroes + villains)
/universe/arc/<id>             - Story arc overview (all issues)
/universe/arc/<id>/issue/new   - Generate next issue in the arc
/universe/issue/<id>           - Read a comic issue (panel-by-panel)
"""
import os

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.character import Character
from ..models.villain import Villain
from ..models.story_arc import StoryArc, ComicIssue, ComicPanel
from ..services.comic_generator import (
    generate_arc_concept,
    generate_arc_cover,
    generate_issue_plan,
    generate_issue_cover,
    generate_panel_image,
)

universe_bp = Blueprint("universe", __name__, url_prefix="/universe")


def _panels_dir() -> str:
    path = os.path.join(current_app.root_path, "static", "uploads", "panels")
    os.makedirs(path, exist_ok=True)
    return path


def _covers_dir() -> str:
    path = os.path.join(current_app.root_path, "static", "uploads", "arc_covers")
    os.makedirs(path, exist_ok=True)
    return path


# ─────────────────────────────────────────────
# UNIVERSE HUB
# ─────────────────────────────────────────────
@universe_bp.route("/")
def universe_hub():
    arcs = StoryArc.query.order_by(StoryArc.arc_number.asc()).all()
    total_heroes = Character.query.count()
    total_villains = Villain.query.count()
    return render_template(
        "universe/hub.html",
        arcs=arcs,
        total_heroes=total_heroes,
        total_villains=total_villains,
    )


# ─────────────────────────────────────────────
# NEW STORY ARC
# ─────────────────────────────────────────────
@universe_bp.route("/arc/new", methods=["GET", "POST"])
def new_arc():
    heroes = Character.query.order_by(Character.superhero_name).all()
    villains = Villain.query.order_by(Villain.villain_name).all()

    if request.method == "GET":
        next_arc_number = (StoryArc.query.count() or 0) + 1
        return render_template(
            "universe/new_arc.html",
            heroes=heroes,
            villains=villains,
            next_arc_number=next_arc_number,
        )

    # POST – user selected heroes/villains; AI generates the arc concept
    selected_hero_ids = request.form.getlist("hero_ids", type=int)
    selected_villain_ids = request.form.getlist("villain_ids", type=int)

    if not selected_hero_ids:
        flash("Pick at least one hero for the story arc.", "warning")
        return redirect(url_for("universe.new_arc"))

    selected_heroes = Character.query.filter(Character.id.in_(selected_hero_ids)).all()
    selected_villains = Villain.query.filter(Villain.id.in_(selected_villain_ids)).all()

    arc_number = (StoryArc.query.count() or 0) + 1

    # AI generates arc title, tagline, summary
    concept = generate_arc_concept(selected_heroes, selected_villains, arc_number)

    arc = StoryArc(
        title=concept.get("title", f"Arc {arc_number}"),
        tagline=concept.get("tagline", ""),
        summary=concept.get("summary", ""),
        arc_number=arc_number,
        status="ongoing",
    )
    arc.heroes = selected_heroes
    arc.villains = selected_villains
    db.session.add(arc)
    db.session.flush()  # get arc.id before generating cover

    # AI generates arc cover image
    cover_filename = generate_arc_cover(arc.title, selected_heroes, selected_villains, _covers_dir())
    arc.cover_image = cover_filename

    db.session.commit()
    flash(f'Story Arc "{arc.title}" has been created! Now generate the first issue.', "success")
    return redirect(url_for("universe.arc_detail", arc_id=arc.id))


# ─────────────────────────────────────────────
# STORY ARC DETAIL
# ─────────────────────────────────────────────
@universe_bp.route("/arc/<int:arc_id>")
def arc_detail(arc_id):
    arc = StoryArc.query.get_or_404(arc_id)
    return render_template("universe/arc_detail.html", arc=arc)


# ─────────────────────────────────────────────
# GENERATE NEXT ISSUE
# ─────────────────────────────────────────────
@universe_bp.route("/arc/<int:arc_id>/issue/new", methods=["POST"])
def new_issue(arc_id):
    arc = StoryArc.query.get_or_404(arc_id)

    issue_number = len(arc.issues) + 1
    total_planned = 6  # arc has up to 6 issues by default

    # AI generates the issue plot + 6 panel descriptions
    plan = generate_issue_plan(
        arc_summary=arc.summary or arc.title,
        issue_number=issue_number,
        total_issues=total_planned,
        heroes=arc.heroes,
        villains=arc.villains,
    )

    issue = ComicIssue(
        arc_id=arc.id,
        issue_number=issue_number,
        title=plan.get("title", f"Issue {issue_number}"),
        summary=plan.get("summary", ""),
    )
    db.session.add(issue)
    db.session.flush()  # need issue.id

    # Generate cover for issue
    cover_filename = generate_issue_cover(issue.title, arc.title, arc.heroes, _covers_dir())
    issue.cover_image = cover_filename

    # Generate panels
    hero_names = ", ".join(h.superhero_name for h in arc.heroes)
    villain_names = ", ".join(v.villain_name for v in arc.villains) if arc.villains else "the villain"

    panels_data = plan.get("panels", [])
    for idx, panel_data in enumerate(panels_data, start=1):
        description = panel_data.get("description", "")
        dialogue = panel_data.get("dialogue", "")

        img_file, img_prompt = generate_panel_image(
            panel_description=description,
            hero_names=hero_names,
            villain_names=villain_names,
            save_dir=_panels_dir(),
        )

        panel = ComicPanel(
            issue_id=issue.id,
            panel_number=idx,
            description=description,
            dialogue=dialogue,
            image_file=img_file,
            image_prompt=img_prompt,
        )
        db.session.add(panel)

    # Mark arc complete if we've hit 6 issues
    if issue_number >= total_planned:
        arc.status = "complete"

    db.session.commit()
    flash(f'Issue #{issue_number} "{issue.title}" has been generated!', "success")
    return redirect(url_for("universe.issue_reader", issue_id=issue.id))


# ─────────────────────────────────────────────
# ISSUE READER (panel-by-panel)
# ─────────────────────────────────────────────
@universe_bp.route("/issue/<int:issue_id>")
def issue_reader(issue_id):
    issue = ComicIssue.query.get_or_404(issue_id)
    arc = issue.arc
    all_issues = arc.issues  # ordered by issue_number

    # prev / next navigation
    current_index = next((i for i, iss in enumerate(all_issues) if iss.id == issue.id), 0)
    prev_issue = all_issues[current_index - 1] if current_index > 0 else None
    next_issue = all_issues[current_index + 1] if current_index < len(all_issues) - 1 else None

    return render_template(
        "universe/issue_reader.html",
        issue=issue,
        arc=arc,
        prev_issue=prev_issue,
        next_issue=next_issue,
    )
