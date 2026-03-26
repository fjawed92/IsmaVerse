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


def _hero_appearance(hero) -> str:
    """Build a compact visual description of a hero from their stored image_prompt or fields."""
    if hero.image_prompt:
        # Extract the costume/appearance section from the stored prompt
        lines = hero.image_prompt.splitlines()
        appearance_lines = []
        in_section = False
        for line in lines:
            if "COSTUME" in line or "CHARACTER DETAILS" in line:
                in_section = True
            if in_section:
                appearance_lines.append(line)
            if in_section and "POWERS" in line and line != "=== POWERS (MUST be visually shown in the image) ===":
                break
        if appearance_lines:
            return " ".join(l.strip() for l in appearance_lines[:10] if l.strip())
    # Fallback: build from fields
    parts = [f"{hero.superhero_name}"]
    if hasattr(hero, "costume_color") and hero.costume_color:
        parts.append(f"wearing {hero.costume_color} costume")
    if hasattr(hero, "cape_color") and hero.cape_color:
        parts.append(f"with {hero.cape_color} cape")
    if hasattr(hero, "hair_color") and hero.hair_color:
        parts.append(f"{hero.hair_color} hair")
    return ", ".join(parts)


def _villain_appearance(villain) -> str:
    """Build a compact visual description of a villain from their stored fields."""
    parts = [f"{villain.villain_name}"]
    if hasattr(villain, "costume_color") and villain.costume_color:
        parts.append(f"wearing {villain.costume_color} costume")
    if hasattr(villain, "hair_color") and villain.hair_color:
        parts.append(f"{villain.hair_color} hair")
    if hasattr(villain, "powers") and villain.powers:
        parts.append(f"with powers: {villain.powers[:80]}")
    return ", ".join(parts)


def generate_arc_cover(arc_title: str, heroes: list, villains: list, save_dir: str) -> str | None:
    hero_names = ", ".join(h.superhero_name for h in heroes) if heroes else "heroes"
    villain_names = ", ".join(v.villain_name for v in villains) if villains else "a villain"
    hero_appearances = "; ".join(_hero_appearance(h) for h in heroes) if heroes else ""
    villain_appearances = "; ".join(_villain_appearance(v) for v in villains) if villains else ""
    prompt = (
        f"Comic book cover art for '{arc_title}'. "
        f"Features the heroes {hero_names} facing off against {villain_names}. "
    )
    if hero_appearances:
        prompt += f"Hero appearances: {hero_appearances}. "
    if villain_appearances:
        prompt += f"Villain appearances: {villain_appearances}. "
    prompt += "Bold title lettering at the top. Dramatic but kid-friendly composition."
    return _generate_image(prompt, save_dir)


# ---------------------------------------------------------------------------
# Issue generation
# ---------------------------------------------------------------------------

def generate_issue_plan(arc_summary: str, issue_number: int, total_issues: int,
                        heroes: list, villains: list,
                        previous_summaries: list | None = None) -> dict:
    """
    Generate the plot for one issue within the arc.
    Returns dict with keys: title, summary, story_text, panels (list of {description, dialogue})
    previous_summaries: list of short summaries from all prior issues, used to maintain continuity.
    """
    hero_names = ", ".join(h.superhero_name for h in heroes) if heroes else "the heroes"
    villain_names = ", ".join(v.villain_name for v in villains) if villains else "the villain"

    # Build continuity context from previous issues
    continuity_block = ""
    if previous_summaries:
        summaries_text = "\n".join(
            f"  Issue {i+1}: {s}" for i, s in enumerate(previous_summaries)
        )
        continuity_block = (
            f"\nPrevious issues in this arc (use these to maintain continuity and build on the story):\n"
            f"{summaries_text}\n"
        )

    system = (
        "You are a creative comic book writer for children aged 6-12. "
        "Stories are adventurous, fun, and teach positive values like teamwork and courage. "
        "Content is never scary or violent. "
        "Maintain continuity with previous issues — build on what came before. "
        "Respond ONLY with valid JSON — no markdown, no code fences."
    )
    user = (
        f"Arc summary: {arc_summary}\n"
        f"{continuity_block}"
        f"Write issue {issue_number} of {total_issues} in this arc.\n"
        f"Heroes: {hero_names}. Villains: {villain_names}.\n\n"
        "Return JSON with exactly these keys:\n"
        '  "title": issue title (max 6 words)\n'
        '  "summary": 2-3 sentences describing this issue (used as a teaser on the arc page)\n'
        '  "story_text": a fun, engaging prose narrative of the full issue story (3-5 paragraphs, '
        'written for kids aged 6-12, using vivid descriptions and exciting action — this is the '
        'full story text displayed alongside the comic panels)\n'
        '  "panels": array of EXACTLY 4 objects, each with:\n'
        '      "description": vivid scene description for image generation (1-2 sentences)\n'
        '      "dialogue": caption or speech bubble text shown to readers (1-2 sentences, fun and snappy)\n'
        "No markdown — raw JSON only."
    )

    raw = _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=1200,
    )
    if not raw:
        return _fallback_issue(issue_number, hero_names, villain_names)

    try:
        data = json.loads(raw)
        # ensure panels exist and are trimmed/padded to exactly 4
        if "panels" not in data or not isinstance(data["panels"], list):
            data["panels"] = _default_panels(hero_names, villain_names)
        data["panels"] = data["panels"][:4]
        while len(data["panels"]) < 4:
            data["panels"].append(_default_panels(hero_names, villain_names)[len(data["panels"])])
        return data
    except json.JSONDecodeError:
        return _fallback_issue(issue_number, hero_names, villain_names)


def _fallback_issue(issue_number: int, hero_names: str, villain_names: str) -> dict:
    return {
        "title": f"Issue {issue_number}",
        "summary": f"{hero_names} face a new challenge from {villain_names}.",
        "story_text": (
            f"In this thrilling issue, {hero_names} discover that {villain_names} is up to no good! "
            f"Using their amazing powers and the strength of teamwork, our heroes spring into action. "
            f"The battle is tough, but {hero_names} never give up. "
            f"With a clever plan and lots of courage, they outsmart {villain_names} and save the day. "
            f"IsmaVerse is safe — for now!"
        ),
        "panels": _default_panels(hero_names, villain_names),
    }


def _default_panels(hero_names: str, villain_names: str) -> list:
    return [
        {"description": f"{hero_names} discover a mysterious clue.", "dialogue": "Something strange is going on..."},
        {"description": f"{villain_names} reveals their dastardly plan.", "dialogue": "You'll never stop me!"},
        {"description": f"{hero_names} team up and use their powers.", "dialogue": "Together we're unstoppable!"},
        {"description": "The day is saved and heroes celebrate.", "dialogue": "IsmaVerse is safe — for now!"},
    ]


def generate_panel_image(panel_description: str, hero_names: str, villain_names: str, save_dir: str,
                         heroes: list = None, villains: list = None) -> tuple[str | None, str]:
    prompt = f"Comic panel: {panel_description} "
    if heroes:
        appearances = "; ".join(_hero_appearance(h) for h in heroes)
        prompt += f"Heroes ({hero_names}) look like: {appearances}. "
    else:
        prompt += f"Characters: {hero_names}. "
    if villains:
        appearances = "; ".join(_villain_appearance(v) for v in villains)
        prompt += f"Villains ({villain_names}) look like: {appearances}. "
    elif villain_names and villain_names != "the villain":
        prompt += f"Villain: {villain_names}. "
    prompt += "Full-colour comic book illustration, dynamic and expressive."
    filename = _generate_image(prompt, save_dir)
    return filename, prompt


def generate_battle_narration(
    fighter1_name: str, fighter1_powers: str,
    fighter2_name: str, fighter2_powers: str,
    winner_name: str,
) -> str | None:
    """Generate a short comic-style narration of a 1v1 battle result."""
    system = (
        "You are a comic book announcer for kids aged 6-12. "
        "Write exciting, fun, and kid-friendly battle narrations. "
        "Never scary or violent — think cartoon action with lots of POW!, BAM!, ZAP! "
        "Keep it to 3-4 short punchy sentences. No markdown."
    )
    user = (
        f"{fighter1_name} (powers: {fighter1_powers}) just battled "
        f"{fighter2_name} (powers: {fighter2_powers}). "
        f"{winner_name} won the battle! "
        "Write a fun, exciting 3-4 sentence narration of how the battle went and how the winner triumphed. "
        "Include at least one comic sound effect like POW! or ZAP!."
    )
    return _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=200,
        temperature=0.9,
    )


def generate_team_battle_narration(
    team1_name: str, team1_members: list,
    team2_name: str, team2_members: list,
    winning_team_name: str,
) -> str | None:
    """Generate a short comic-style narration of a team battle result."""
    def member_summary(members):
        return ", ".join(
            f"{m['name']} ({m.get('powers','???')[:40]})" for m in members
        )

    system = (
        "You are a comic book announcer for kids aged 6-12. "
        "Write exciting, fun, kid-friendly team battle narrations. "
        "Never scary or violent — think cartoon action. "
        "Keep it to 4-5 short sentences with comic sound effects. No markdown."
    )
    user = (
        f"Epic team battle!\n"
        f"{team1_name}: {member_summary(team1_members)}\n"
        f"{team2_name}: {member_summary(team2_members)}\n"
        f"{winning_team_name} won! "
        "Write an exciting 4-5 sentence comic narration of how the team battle went. "
        "Mention at least 2 team members by name and include comic sound effects like POW!, BOOM!, ZAP!."
    )
    return _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=300,
        temperature=0.9,
    )


def generate_issue_cover(issue_title: str, arc_title: str, heroes: list, save_dir: str) -> str | None:
    hero_names = ", ".join(h.superhero_name for h in heroes) if heroes else "heroes"
    hero_appearances = "; ".join(_hero_appearance(h) for h in heroes) if heroes else ""
    prompt = (
        f"Comic book cover for issue titled '{issue_title}' (part of '{arc_title}'). "
        f"Features {hero_names} in a heroic pose. "
    )
    if hero_appearances:
        prompt += f"Hero appearances: {hero_appearances}. "
    prompt += "Bold lettering, vivid colours, exciting composition."
    return _generate_image(prompt, save_dir)
