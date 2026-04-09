"""
Coalition-wide volunteer dispatch broadcast.

Sends a dispatch request to all partner orgs simultaneously.
Each org sees only the request details — never other orgs' volunteer lists.
Per-org data isolation is enforced structurally: BroadcastResponse contains
only the requesting org's coverage summary, not a merged list.

This implements the Coalition Coordination bounded context from the domain model.
Data sharing applies the strictest partner's handling rules (see CLAUDE.md Privacy).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.dispatch.matcher import VolunteerMatcher
from src.dispatch.models import DispatchMatch, DispatchRequest, Volunteer


@dataclass(frozen=True)
class OrgVolunteerPool:
    """A single org's volunteer pool — opaque to other coalition partners."""
    org_id: str
    volunteers: list[Volunteer]


@dataclass
class OrgCoverage:
    """Coverage summary for one org — shared with the broadcast originator."""
    org_id: str
    matched_count: int
    top_match_score: Optional[float]
    accepted: bool = False
    accepted_at: Optional[datetime] = None


@dataclass
class BroadcastResponse:
    """Aggregate result of a coalition broadcast.

    `org_coverage` entries tell the originator how many matches each
    partner org found. Individual volunteer identities are never included.
    """
    request_id: str
    campaign_id: str
    org_coverage: list[OrgCoverage]
    broadcast_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )

    @property
    def total_available(self) -> int:
        return sum(c.matched_count for c in self.org_coverage)

    @property
    def responding_orgs(self) -> int:
        return sum(1 for c in self.org_coverage if c.matched_count > 0)


class CoalitionBroadcaster:
    """Dispatch a request to all coalition partner orgs.

    Each org's volunteer pool is processed independently.
    The resulting BroadcastResponse contains only coverage counts —
    no individual volunteer data crosses org boundaries.
    """

    def __init__(self, matcher: Optional[VolunteerMatcher] = None) -> None:
        self._matcher = matcher or VolunteerMatcher()

    def broadcast(
        self,
        request: DispatchRequest,
        org_pools: list[OrgVolunteerPool],
    ) -> BroadcastResponse:
        """Send dispatch request to all orgs and collect coverage summaries.

        Args:
            request: The dispatch request to broadcast.
            org_pools: Each participating org's volunteer pool.

        Returns:
            BroadcastResponse with per-org match counts.
            Individual volunteer IDs are not included in the response.
        """
        coverage: list[OrgCoverage] = []

        for pool in org_pools:
            matches = self._matcher.match(request, pool.volunteers, max_results=10)
            top_score = matches[0].match_score if matches else None
            coverage.append(
                OrgCoverage(
                    org_id=pool.org_id,
                    matched_count=len(matches),
                    top_match_score=top_score,
                )
            )

        return BroadcastResponse(
            request_id=request.request_id,
            campaign_id=request.campaign_id,
            org_coverage=coverage,
        )

    def accept(
        self,
        response: BroadcastResponse,
        org_id: str,
    ) -> BroadcastResponse:
        """Mark an org as having accepted the broadcast request.

        Returns an updated BroadcastResponse (responses are otherwise immutable).
        """
        updated_coverage = []
        for entry in response.org_coverage:
            if entry.org_id == org_id:
                updated_coverage.append(
                    OrgCoverage(
                        org_id=entry.org_id,
                        matched_count=entry.matched_count,
                        top_match_score=entry.top_match_score,
                        accepted=True,
                        accepted_at=datetime.now(tz=timezone.utc),
                    )
                )
            else:
                updated_coverage.append(entry)

        return BroadcastResponse(
            request_id=response.request_id,
            campaign_id=response.campaign_id,
            org_coverage=updated_coverage,
            broadcast_at=response.broadcast_at,
        )
