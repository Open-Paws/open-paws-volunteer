"""
Tests for engagement tracker and XP awarder.
"""
import pytest
from datetime import datetime, timedelta, timezone

from src.dispatch.models import Volunteer
from src.engagement.tracker import (
    ENGAGEMENT_FLOOR,
    REACTIVATION_THRESHOLD,
    at_risk_volunteers,
    engagement_status,
    log_activity,
    weekly_decay_pass,
)
from src.engagement.xp import XPAwarder, XP_TABLE


def make_volunteer(volunteer_id: str, engagement_score: float = 1.0) -> Volunteer:
    return Volunteer(
        volunteer_id=volunteer_id,
        org_id="org-test",
        skills=[],
        languages=["en"],
        timezone="UTC",
        engagement_score=engagement_score,
    )


class TestEngagementTracker:
    def test_log_activity_raises_for_unknown_type(self):
        """Unknown activity types must raise ValueError, not silently pass."""
        volunteer = make_volunteer("vol-001")
        with pytest.raises(ValueError, match="Unknown activity type"):
            log_activity(volunteer, "not_a_real_activity")

    def test_log_activity_boosts_score(self):
        """Logging a known activity must increase engagement_score."""
        volunteer = make_volunteer("vol-001", engagement_score=0.5)
        updated = log_activity(volunteer, "dispatch_completed")
        assert updated.engagement_score > 0.5

    def test_engagement_score_capped_at_one(self):
        """Engagement score must never exceed 1.0 regardless of activity stacking."""
        volunteer = make_volunteer("vol-001", engagement_score=0.95)
        updated = log_activity(volunteer, "dispatch_completed")
        assert updated.engagement_score <= 1.0

    def test_weekly_decay_reduces_score(self):
        """A volunteer with no recent activity must have a lower score after decay."""
        old_date = datetime.now(tz=timezone.utc) - timedelta(days=14)
        volunteer = make_volunteer("vol-001", engagement_score=0.8)
        volunteer = volunteer.__class__(
            **{**volunteer.__dict__, "last_active": old_date}
        )
        updated = weekly_decay_pass([volunteer])
        assert updated[0].engagement_score < 0.8

    def test_weekly_decay_respects_floor(self):
        """Decay must not push engagement_score below ENGAGEMENT_FLOOR."""
        old_date = datetime.now(tz=timezone.utc) - timedelta(days=365)
        volunteer = make_volunteer("vol-001", engagement_score=ENGAGEMENT_FLOOR)
        volunteer = volunteer.__class__(
            **{**volunteer.__dict__, "last_active": old_date}
        )
        updated = weekly_decay_pass([volunteer])
        assert updated[0].engagement_score >= ENGAGEMENT_FLOOR

    def test_recently_active_volunteer_not_decayed(self):
        """Volunteers active within the last 7 days must not be decayed."""
        recent = datetime.now(tz=timezone.utc) - timedelta(days=2)
        volunteer = make_volunteer("vol-001", engagement_score=0.8)
        volunteer = volunteer.__class__(
            **{**volunteer.__dict__, "last_active": recent}
        )
        updated = weekly_decay_pass([volunteer])
        assert updated[0].engagement_score == 0.8

    def test_at_risk_volunteers_filters_correctly(self):
        """at_risk_volunteers must return only those below the threshold."""
        healthy = make_volunteer("vol-healthy", engagement_score=0.8)
        at_risk = make_volunteer("vol-risk", engagement_score=0.2)
        borderline = make_volunteer("vol-border", engagement_score=REACTIVATION_THRESHOLD)

        result = at_risk_volunteers([healthy, at_risk, borderline])

        ids = [v.volunteer_id for v in result]
        assert "vol-risk" in ids
        assert "vol-healthy" not in ids
        # Exactly at threshold is not at-risk (< not <=)
        assert "vol-border" not in ids

    def test_engagement_status_labels(self):
        """Status labels must reflect correct score ranges."""
        assert engagement_status(make_volunteer("v", 0.8)) == "Healthy"
        assert engagement_status(make_volunteer("v", 0.5)) == "Warning"
        assert engagement_status(make_volunteer("v", 0.1)) == "At-Risk"


class TestXPAwarder:
    def test_award_known_activity(self):
        """Award must return correct XP for a known activity."""
        awarder = XPAwarder()
        award = awarder.award("vol-001", "dispatch_completed")
        assert award.xp_amount == XP_TABLE["dispatch_completed"]
        assert award.volunteer_id == "vol-001"

    def test_award_raises_for_unknown_activity(self):
        """Unknown activity keys must raise ValueError."""
        awarder = XPAwarder()
        with pytest.raises(ValueError, match="Unknown XP activity"):
            awarder.award("vol-001", "not_an_activity")

    def test_sync_returns_bool(self):
        """sync_to_platform must return a bool (True = success, False = failure)."""
        awarder = XPAwarder()
        award = awarder.award("vol-001", "call_completed")
        result = awarder.sync_to_platform(award)
        assert isinstance(result, bool)
