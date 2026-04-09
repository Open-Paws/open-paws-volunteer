"""
Volunteer engagement tracking and decay detection.

Adapted from VolunteerManager engagement decay patterns.

Decay model:
  - engagement_score starts at 1.0 on first activity
  - decreases by DECAY_PER_WEEK (0.1) for each week without activity
  - floor at ENGAGEMENT_FLOOR (0.1) — never reaches zero, always reachable
  - volunteers below REACTIVATION_THRESHOLD (0.3) are flagged NEEDS_REACTIVATION

weekly_decay_pass() is designed to run as a cron job (e.g. every Monday 06:00 UTC).
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.dispatch.models import Volunteer

DECAY_PER_WEEK: float = 0.1
ENGAGEMENT_FLOOR: float = 0.1
REACTIVATION_THRESHOLD: float = 0.3
ACTIVITY_BOOST: dict[str, float] = {
    "dispatch_accepted": 0.20,
    "dispatch_completed": 0.30,
    "call_completed": 0.10,
    "hours_logged": 0.15,
    "profile_updated": 0.05,
}


def log_activity(
    volunteer: Volunteer,
    activity_type: str,
    *,
    at: Optional[datetime] = None,
) -> Volunteer:
    """Return an updated volunteer after recording an activity.

    Raises ValueError for unknown activity types so callers cannot silently
    pass misspelled activity names without feedback.
    """
    if activity_type not in ACTIVITY_BOOST:
        raise ValueError(
            f"Unknown activity type: {activity_type!r}. "
            f"Valid types: {sorted(ACTIVITY_BOOST)}"
        )
    boost = ACTIVITY_BOOST[activity_type]
    new_score = min(1.0, volunteer.engagement_score + boost)
    return replace(
        volunteer,
        engagement_score=round(new_score, 4),
        last_active=at or datetime.now(tz=timezone.utc),
    )


def weekly_decay_pass(volunteers: list[Volunteer]) -> list[Volunteer]:
    """Apply one week of engagement decay to all volunteers.

    Intended to run as a cron job. Volunteers with recent activity
    (last_active within the past 7 days) are skipped.
    Returns the full list with updated engagement scores.
    """
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=7)
    updated: list[Volunteer] = []
    for v in volunteers:
        last = v.last_active
        if last is not None and last.replace(tzinfo=timezone.utc) >= cutoff:
            updated.append(v)
            continue
        new_score = max(ENGAGEMENT_FLOOR, v.engagement_score - DECAY_PER_WEEK)
        updated.append(replace(v, engagement_score=round(new_score, 4)))
    return updated


def at_risk_volunteers(volunteers: list[Volunteer]) -> list[Volunteer]:
    """Return volunteers whose engagement score has fallen below the reactivation threshold."""
    return [v for v in volunteers if v.engagement_score < REACTIVATION_THRESHOLD]


def engagement_status(volunteer: Volunteer) -> str:
    """Human-readable engagement health label for dashboard display."""
    score = volunteer.engagement_score
    if score >= 0.7:
        return "Healthy"
    if score >= REACTIVATION_THRESHOLD:
        return "Warning"
    return "At-Risk"
