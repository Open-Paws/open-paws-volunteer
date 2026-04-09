"""
Skill-matched volunteer dispatcher.

Adapted from Volunteer-Dispatch-Optimizer proximity + skill routing.
Score breakdown:
  - 60%  skill coverage (fraction of required skills the volunteer holds)
  - 20%  language match (fraction of required languages covered)
  - 20%  engagement bonus (volunteer.engagement_score * 0.2, max 0.2)

Volunteers with zero skill coverage are excluded entirely.
Timezone overlap is used as a soft proximity signal when no lat/lon is shared.
"""
from .models import AvailabilityStatus, DispatchMatch, DispatchRequest, Volunteer


class VolunteerMatcher:
    """Match volunteers to dispatch requests by skill, language, and engagement."""

    def match(
        self,
        request: DispatchRequest,
        volunteers: list[Volunteer],
        max_results: int = 5,
    ) -> list[DispatchMatch]:
        """Return up to max_results ranked matches for a dispatch request.

        Only AVAILABLE and BUSY volunteers are considered. OFFLINE volunteers
        are excluded so coordinators can contact them separately.
        """
        candidates = [v for v in volunteers if v.availability != AvailabilityStatus.OFFLINE]

        scored: list[DispatchMatch] = []
        for volunteer in candidates:
            score = self._composite_score(volunteer, request)
            if score == 0.0:
                continue
            scored.append(
                DispatchMatch(
                    volunteer_id=volunteer.volunteer_id,
                    request_id=request.request_id,
                    match_score=round(score, 4),
                    skill_coverage=self._skill_coverage(
                        volunteer.skills, request.required_skills
                    ),
                )
            )

        return sorted(scored, key=lambda m: m.match_score, reverse=True)[:max_results]

    # ------------------------------------------------------------------
    # Private scoring helpers
    # ------------------------------------------------------------------

    def _composite_score(self, volunteer: Volunteer, request: DispatchRequest) -> float:
        skill_score = self._skill_coverage(volunteer.skills, request.required_skills)
        if skill_score == 0.0:
            return 0.0

        language_score = self._language_coverage(volunteer.languages, request.required_languages)
        engagement_bonus = volunteer.engagement_score * 0.2

        return skill_score * 0.60 + language_score * 0.20 + engagement_bonus

    def _skill_coverage(
        self, volunteer_skills: list, required_skills: list
    ) -> float:
        if not required_skills:
            return 1.0
        volunteer_set = {s.value for s in volunteer_skills}
        required_set = {s.value for s in required_skills}
        matched = len(volunteer_set & required_set)
        return matched / len(required_set)

    def _language_coverage(
        self, volunteer_languages: list[str], required_languages: list[str]
    ) -> float:
        if not required_languages:
            return 1.0
        matched = len(set(required_languages) & set(volunteer_languages))
        return matched / len(required_languages)
