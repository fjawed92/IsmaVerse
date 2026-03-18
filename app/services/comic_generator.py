"""
AI Comic Universe Generator
============================
Uses OpenAI GPT-4o-mini for story generation and gpt-image-1 for panel images.
All content is kept kid-friendly (ages 6-12).
"""
import base64
import json
import os
import uuid
import urllib.error
import urllib.request

from flask import current_app


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

STYLE_PROMPT = (
    "Kid-friendly comic book panel. Thick black outlines. Flat bold colours. "
    "Cartoonish, rounded shapes, big expressive eyes. Dynamic action pose. "
    "Energetic, fun, never scary. Sound-effect burst if dramatic."
)


def _openai_api_key() -> str | None:
    return current_app.config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")


def _chat(messages: list, max_tokens: int = 600, temperature: float = 0.85) -> str | None:
    """Call GPT-4o-mini and return the assistant reply, or None on failure."""
    api_key = _openai_api_key()
    if not api_key:
        return None

    payload = json.dumps(
        {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as exc:
        current_app.logger.error("OpenAI chat error: %s", exc.read().decode("utf-8"))
        return None


def _generate_image(prompt: str, save_dir: str) -> str | None:
    """Call gpt-image-1, save the result, return filename or None."""
    api_key = _openai_api_key()
    if not api_key:
        return None

    full_prompt = f"{prompt}\n\n{STYLE_PROMPT}"

    payload = json.dumps(
        {"model": "gpt-image-1", "prompt": full_prompt, "size": "1024x1024"}
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        current_app.logger.error("OpenAI image error: %s", exc.read().decode("utf-8"))
        return None

    image_data = body["data"][0]
    if "b64_json" in image_data:
        image_bytes = base64.b64decode(image_data["b64_json"])
    elif "url" in image_data:
        with urllib.request.urlopen(image_data["url"]) as ir:
            image_bytes = ir.read()
    else:
        return None

    os.makedirs(save_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    with open(os.path.join(save_dir, filename), "wb") as f:
        f.write(image_bytes)
    return filename


# ---------------------------------------------------------------------------
# Story Arc generation
# ---------------------------------------------------------------------------

def generate_arc_concept(heroes: list, villains: list, arc_number: int) -> dict:
    """
    Ask GPT to invent a story arc for the given heroes & villains.
    Returns dict with keys: title, tagline, summary
    """
    hero_names = ", ".join(h.superhero_name for h in heroes) if heroes else "the heroes"
    villain_names = ", ".join(v.villain_name for v in villains) if villains else "a mysterious villain"
    hero_powers = "; ".join(f"{h.superhero_name}: {h.powers}" for h in heroes) if heroes else ""
    villain_plans = "; ".join(f"{v.villain_name}: {v.evil_plan}" for v in villains) if villains else ""

    system = (
        "You are a creative comic book writer for children aged 6-12. "
        "Stories are adventurous, fun, and never scary or violent. "
        "Heroes always learn a lesson or show teamwork. "
        "Respond ONLY with valid JSON."
    )
    user = (
        f"Create story arc #{arc_number} for an IsmaVerse comic universe.\n"
        f"Heroes: {hero_names}\nHero powers: {hero_powers}\n"
        f"Villains: {villain_names}\nVillain plans: {villain_plans}\n\n"
        "Return JSON with exactly these keys:\n"
        '  "title": short exciting arc title (max 8 words)\n'
        '  "tagline": one punchy sentence teaser\n'
        '  "summary": 3-4 sentences describing the overall arc story\n'
        "No markdown, no code fences — raw JSON only."
    )

    raw = _chat([{"role": "system", "content": system}, {"role": "user", "content": user}], max_tokens=400)
    if not raw:
        return {
            "title": f"Arc {arc_number}: New Adventure",
            "tagline": "A brand-new threat is rising!",
            "summary": "Our heroes must band together to face an unknown danger.",
        }
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "title": f"Arc {arc_number}: New Adventure",
            "tagline": "A brand-new threat is rising!",
            "summary": raw,
        }


def generate_arc_cover(arc_title: str, heroes: list, villains: list, save_dir: str) -> str | None:
    hero_names = ", ".join(h.superhero_name for h in heroes) if heroes else "heroes"
    villain_names = ", ".join(v.villain_name for v in villains) if villains else "a villain"
    prompt = (
        f"Comic book cover art for '{arc_title}'. "
        f"Features the heroes {hero_names} facing off against {villain_names}. "
        "Bold title lettering at the top. Dramatic but kid-friendly composition."
    )
    return _generate_image(prompt, save_dir)


# ---------------------------------------------------------------------------
# Issue generation
# ---------------------------------------------------------------------------

def generate_issue_plan(arc_summary: str, issue_number: int, total_issues: int,
                        heroes: list, villains: list) -> dict:
    """
    Generate the plot for one issue within the arc.
    Returns dict with keys: title, summary, panels (list of {description, dialogue})
    """
    hero_names = ", ".join(h.superhero_name for h in heroes) if heroes else "the heroes"
    villain_names = ", ".join(v.villain_name for v in villains) if villains else "the villain"

    system = (
        "You are a kid-friendly comic book writer (ages 6-12). "
        "Content is fun, adventurous, and teaches positive values. "
        "Respond ONLY with valid JSON — no markdown, no code fences."
    )
    user = (
        f"Arc summary: {arc_summary}\n"
        f"Write issue {issue_number} of {total_issues} in this arc.\n"
        f"Heroes: {hero_names}. Villains: {villain_names}.\n\n"
        "Return JSON with exactly these keys:\n"
        '  "title": issue title (max 6 words)\n'
        '  "summary": 2-3 sentences describing this issue\n'
        '  "panels": array of 6 objects, each with:\n'
        '      "description": vivid scene description for image generation (1-2 sentences)\n'
        '      "dialogue": caption or speech bubble text shown to readers (1-2 sentences, fun and snappy)\n'
        "No markdown — raw JSON only."
    )

    raw = _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=800,
    )
    if not raw:
        return _fallback_issue(issue_number, hero_names, villain_names)

    try:
        data = json.loads(raw)
        # ensure panels exist
        if "panels" not in data or not isinstance(data["panels"], list):
            data["panels"] = _default_panels(hero_names, villain_names)
        return data
    except json.JSONDecodeError:
        return _fallback_issue(issue_number, hero_names, villain_names)


def _fallback_issue(issue_number: int, hero_names: str, villain_names: str) -> dict:
    return {
        "title": f"Issue {issue_number}",
        "summary": f"{hero_names} face a new challenge from {villain_names}.",
        "panels": _default_panels(hero_names, villain_names),
    }


def _default_panels(hero_names: str, villain_names: str) -> list:
    return [
        {"description": f"{hero_names} discover a mysterious clue.", "dialogue": "Something strange is going on..."},
        {"description": f"{villain_names} reveals their dastardly plan.", "dialogue": "You'll never stop me!"},
        {"description": f"{hero_names} team up and use their powers.", "dialogue": "Together we're unstoppable!"},
        {"description": "An epic showdown begins.", "dialogue": "POW! BOOM! ZAP!"},
        {"description": f"{hero_names} outsmart the villain with teamwork.", "dialogue": "Gotcha!"},
        {"description": "The day is saved and heroes celebrate.", "dialogue": "IsmaVerse is safe — for now!"},
    ]


def generate_panel_image(panel_description: str, hero_names: str, villain_names: str, save_dir: str) -> tuple[str | None, str]:
    prompt = (
        f"Comic panel: {panel_description} "
        f"Characters: {hero_names} and {villain_names}. "
        "Full-colour comic book illustration, dynamic and expressive."
    )
    filename = _generate_image(prompt, save_dir)
    return filename, prompt


def generate_issue_cover(issue_title: str, arc_title: str, heroes: list, save_dir: str) -> str | None:
    hero_names = ", ".join(h.superhero_name for h in heroes) if heroes else "heroes"
    prompt = (
        f"Comic book cover for issue titled '{issue_title}' (part of '{arc_title}'). "
        f"Features {hero_names} in a heroic pose. "
        "Bold lettering, vivid colours, exciting composition."
    )
    return _generate_image(prompt, save_dir)
