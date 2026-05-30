"""Daily reading-streak tracking + milestone rewards.

Anonymous users get an equivalent localStorage streak in main.js; this
module is the server-side source of truth for logged-in kids.
"""

from datetime import date, timedelta

from ..extensions import db
from ..models.profile import ReadingStreak
from .badges import record_badge_progress

# Streak milestones that unlock a reward badge (see badges.py defs).
STREAK_BADGES = {
    3: "streak-3",
    7: "streak-7",
}


def _get_or_create_streak(user) -> ReadingStreak:
    streak = ReadingStreak.query.filter_by(user_id=user.id).first()
    if not streak:
        streak = ReadingStreak(user_id=user.id)
        db.session.add(streak)
        db.session.commit()
    return streak


def record_streak_ping(user, today: date | None = None) -> dict:
    """Register activity for *today* and update the streak.

    Returns ``{current, longest, total, just_incremented, unlocked}``.
    Calling more than once a day is a no-op for the count.
    """
    today = today or date.today()
    streak = _get_or_create_streak(user)
    unlocked = []
    just_incremented = False

    last = streak.last_active_date
    if last == today:
        # Already counted today — nothing changes.
        return {
            "current": streak.current_streak,
            "longest": streak.longest_streak,
            "total": streak.total_active_days,
            "just_incremented": False,
            "unlocked": [],
        }

    if last == today - timedelta(days=1):
        streak.current_streak += 1
    else:
        streak.current_streak = 1

    streak.last_active_date = today
    streak.total_active_days += 1
    streak.longest_streak = max(streak.longest_streak, streak.current_streak)
    just_incremented = True

    db.session.add(streak)
    db.session.commit()

    # Milestone rewards
    badge_slug = STREAK_BADGES.get(streak.current_streak)
    if badge_slug:
        record_badge_progress(user, badge_slug)
        unlocked.append(badge_slug)

    return {
        "current": streak.current_streak,
        "longest": streak.longest_streak,
        "total": streak.total_active_days,
        "just_incremented": just_incremented,
        "unlocked": unlocked,
    }


def get_streak(user) -> dict:
    streak = ReadingStreak.query.filter_by(user_id=user.id).first()
    if not streak:
        return {"current": 0, "longest": 0, "total": 0}
    return {
        "current": streak.current_streak,
        "longest": streak.longest_streak,
        "total": streak.total_active_days,
    }
