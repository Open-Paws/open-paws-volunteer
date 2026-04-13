"""
Tests for VolunteerMatcher.

Every test fails when the behavior it covers is broken (per advocacy testing standards).
"""
from src.dispatch.matcher import VolunteerMatcher
from src.dispatch.models import (
    AvailabilityStatus,
    DispatchRequest,
    SkillArea,
    Urgency,
    Volunteer,
)


def make_volunteer(
    volunteer_id: str,
    skills: list[SkillArea],
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
    languages: list[str] | None = None,
    engagement_score: float = 1.0,
) -> Volunteer:
    return Volunteer(
        volunteer_id=volunteer_id,
        org_id="org-test",
        skills=skills,
        languages=languages or ["en"],
        timezone="UTC",
        availability=availability,
        engagement_score=engagement_score,
    )


def make_request(
    required_skills: list[SkillArea],
    required_languages: list[str] | None = None,
) -> DispatchRequest:
    return DispatchRequest(
        request_id="req-001",
        campaign_id="campaign-001",
        required_skills=required_skills,
        required_languages=required_languages or [],
        urgency=Urgency.THIS_WEEK,
        description="Test dispatch",
        location_hint=None,
    )


class TestVolunteerMatcher:
    def test_offline_volunteer_excluded(self):
        """OFFLINE volunteers must not appear in matches even with perfect skills."""
        matcher = VolunteerMatcher()
        volunteer = make_volunteer(
            "vol-offline",
            [SkillArea.LEGAL],
            availability=AvailabilityStatus.OFFLINE,
        )
        request = make_request([SkillArea.LEGAL])

        matches = matcher.match(request, [volunteer])

        assert matches == [], "OFFLINE volunteer should be excluded from matches"

    def test_zero_skill_coverage_excluded(self):
        """Volunteers with no matching skills must be excluded."""
        matcher = VolunteerMatcher()
        volunteer = make_volunteer("vol-technical", [SkillArea.TECHNICAL])
        request = make_request([SkillArea.LEGAL])

        matches = matcher.match(request, [volunteer])

        assert matches == [], "Volunteer with no matching skills should return empty list"

    def test_full_skill_match_returns_top_score(self):
        """A volunteer with all required skills and high engagement scores near 1.0."""
        matcher = VolunteerMatcher()
        volunteer = make_volunteer(
            "vol-top",
            [SkillArea.LEGAL, SkillArea.COMMUNICATIONS],
            engagement_score=1.0,
        )
        request = make_request([SkillArea.LEGAL, SkillArea.COMMUNICATIONS])

        matches = matcher.match(request, [volunteer])

        assert len(matches) == 1
        assert matches[0].match_score > 0.75
        assert matches[0].skill_coverage == 1.0

    def test_partial_skill_match_lower_score_than_full(self):
        """Partial skill match must score lower than full skill match."""
        matcher = VolunteerMatcher()
        full_match = make_volunteer("vol-full", [SkillArea.LEGAL, SkillArea.MEDICAL])
        partial_match = make_volunteer("vol-partial", [SkillArea.LEGAL])
        request = make_request([SkillArea.LEGAL, SkillArea.MEDICAL])

        matches = matcher.match(request, [full_match, partial_match], max_results=2)

        assert len(matches) == 2
        assert matches[0].volunteer_id == "vol-full", "Full match should rank first"
        assert matches[0].match_score > matches[1].match_score

    def test_max_results_respected(self):
        """Matcher must return at most max_results volunteers."""
        matcher = VolunteerMatcher()
        volunteers = [
            make_volunteer(f"vol-{i}", [SkillArea.PHONE_BANKING])
            for i in range(10)
        ]
        request = make_request([SkillArea.PHONE_BANKING])

        matches = matcher.match(request, volunteers, max_results=3)

        assert len(matches) <= 3

    def test_higher_engagement_ranks_higher_when_skills_equal(self):
        """Between equally skilled volunteers, higher engagement wins."""
        matcher = VolunteerMatcher()
        low_engagement = make_volunteer(
            "vol-low", [SkillArea.TRANSLATION], engagement_score=0.2
        )
        high_engagement = make_volunteer(
            "vol-high", [SkillArea.TRANSLATION], engagement_score=0.9
        )
        request = make_request([SkillArea.TRANSLATION])

        matches = matcher.match(request, [low_engagement, high_engagement], max_results=2)

        assert matches[0].volunteer_id == "vol-high", "Higher engagement should rank first"

    def test_language_requirement_reduces_score(self):
        """A volunteer missing a required language must score lower than one who has it."""
        matcher = VolunteerMatcher()
        with_language = make_volunteer(
            "vol-lang", [SkillArea.COMMUNICATIONS], languages=["en", "hi"]
        )
        without_language = make_volunteer(
            "vol-no-lang", [SkillArea.COMMUNICATIONS], languages=["en"]
        )
        request = make_request([SkillArea.COMMUNICATIONS], required_languages=["hi"])

        matches = matcher.match(
            request, [with_language, without_language], max_results=2
        )

        # Both should appear (skill coverage > 0), but with_language scores higher
        ids = [m.volunteer_id for m in matches]
        assert "vol-lang" in ids
        lang_score = next(m.match_score for m in matches if m.volunteer_id == "vol-lang")
        no_lang_score = next(
            m.match_score for m in matches if m.volunteer_id == "vol-no-lang"
        )
        assert lang_score > no_lang_score

    def test_busy_volunteer_included(self):
        """BUSY volunteers should still appear in matches (not OFFLINE)."""
        matcher = VolunteerMatcher()
        volunteer = make_volunteer(
            "vol-busy", [SkillArea.LEGAL], availability=AvailabilityStatus.BUSY
        )
        request = make_request([SkillArea.LEGAL])

        matches = matcher.match(request, [volunteer])

        assert len(matches) == 1, "BUSY volunteer with matching skills should be included"
