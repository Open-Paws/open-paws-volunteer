"""
FastAPI server for open-paws-volunteer coordination platform.

Endpoints follow the seven-concern baseline:
  - Privacy: volunteer location not stored, call content never returned
  - Security: pseudonymous IDs throughout, no PII in responses
  - Accessibility: all responses are JSON with consistent error shapes
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.dispatch.matcher import VolunteerMatcher
from src.dispatch.models import (
    AvailabilityStatus,
    DispatchMatch,
    DispatchRequest,
    SkillArea,
    Urgency,
    Volunteer,
)
from src.coalition.broadcast import CoalitionBroadcaster, OrgVolunteerPool
from src.engagement.tracker import at_risk_volunteers, engagement_status, log_activity
from src.phone_banking.outcome_logger import CallOutcome, create_record, summarise_outcomes

app = FastAPI(
    title="Open Paws Volunteer",
    description="Volunteer coordination for animal advocacy coalitions",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: tighten to platform origin in production
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory stores (replace with sqlite-utils persistence in production)
# ---------------------------------------------------------------------------
_volunteers: dict[str, Volunteer] = {}
_dispatch_requests: dict[str, DispatchRequest] = {}
_matches: dict[str, list[DispatchMatch]] = {}   # request_id -> matches
_call_records: list[Any] = []

_matcher = VolunteerMatcher()
_broadcaster = CoalitionBroadcaster(_matcher)


# ---------------------------------------------------------------------------
# Pydantic request/response schemas
# ---------------------------------------------------------------------------

class VolunteerCreateRequest(BaseModel):
    org_id: str
    skills: list[SkillArea]
    languages: list[str] = Field(default_factory=list)
    timezone: str = "UTC"


class DispatchRequestCreate(BaseModel):
    campaign_id: str
    required_skills: list[SkillArea]
    required_languages: list[str] = Field(default_factory=list)
    urgency: Urgency = Urgency.THIS_WEEK
    description: str
    location_hint: str | None = None
    max_volunteers: int = Field(default=1, ge=1, le=20)


class CallLogRequest(BaseModel):
    campaign_id: str
    volunteer_id: str
    contact_id: str
    outcome: CallOutcome
    duration_seconds: int = Field(default=0, ge=0)
    notes: str | None = None


class BroadcastRequest(BaseModel):
    campaign_id: str
    required_skills: list[SkillArea]
    required_languages: list[str] = Field(default_factory=list)
    urgency: Urgency = Urgency.THIS_WEEK
    description: str
    org_ids: list[str]  # Which coalition orgs to include in the broadcast


# ---------------------------------------------------------------------------
# Volunteer endpoints
# ---------------------------------------------------------------------------

@app.post("/volunteers", status_code=status.HTTP_201_CREATED)
def create_volunteer(body: VolunteerCreateRequest) -> dict:
    """Register a volunteer. Returns a pseudonymous volunteer_id."""
    volunteer_id = f"vol_{uuid.uuid4().hex[:12]}"
    volunteer = Volunteer(
        volunteer_id=volunteer_id,
        org_id=body.org_id,
        skills=body.skills,
        languages=body.languages,
        timezone=body.timezone,
    )
    _volunteers[volunteer_id] = volunteer
    return {"volunteer_id": volunteer_id, "org_id": body.org_id}


@app.get("/volunteers/available")
def list_available_volunteers() -> list[dict]:
    """Return all volunteers who are currently AVAILABLE."""
    available = [
        v for v in _volunteers.values()
        if v.availability == AvailabilityStatus.AVAILABLE
    ]
    return [
        {
            "volunteer_id": v.volunteer_id,
            "org_id": v.org_id,
            "skills": [s.value for s in v.skills],
            "languages": v.languages,
            "engagement_status": engagement_status(v),
        }
        for v in available
    ]


# ---------------------------------------------------------------------------
# Dispatch endpoints
# ---------------------------------------------------------------------------

@app.post("/dispatch/request", status_code=status.HTTP_201_CREATED)
def create_dispatch_request(body: DispatchRequestCreate) -> dict:
    """Create a dispatch request and auto-match available volunteers."""
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    request = DispatchRequest(
        request_id=request_id,
        campaign_id=body.campaign_id,
        required_skills=body.required_skills,
        required_languages=body.required_languages,
        urgency=body.urgency,
        description=body.description,
        location_hint=body.location_hint,
        max_volunteers=body.max_volunteers,
    )
    _dispatch_requests[request_id] = request

    volunteers = list(_volunteers.values())
    matches = _matcher.match(request, volunteers, max_results=body.max_volunteers)
    _matches[request_id] = matches

    return {
        "request_id": request_id,
        "matched_count": len(matches),
        "top_matches": [
            {
                "volunteer_id": m.volunteer_id,
                "match_score": m.match_score,
                "skill_coverage": m.skill_coverage,
            }
            for m in matches[:3]
        ],
    }


@app.post("/dispatch/{request_id}/accept")
def accept_dispatch(request_id: str, volunteer_id: str) -> dict:
    """Record a volunteer accepting a dispatch request."""
    if request_id not in _dispatch_requests:
        raise HTTPException(status_code=404, detail="Dispatch request not found")
    if volunteer_id not in _volunteers:
        raise HTTPException(status_code=404, detail="Volunteer not found")

    volunteer = _volunteers[volunteer_id]
    updated = log_activity(volunteer, "dispatch_accepted")
    _volunteers[volunteer_id] = updated

    return {"accepted": True, "volunteer_id": volunteer_id, "request_id": request_id}


# ---------------------------------------------------------------------------
# Call logging endpoints
# ---------------------------------------------------------------------------

@app.post("/calls/log", status_code=status.HTTP_201_CREATED)
def log_call(body: CallLogRequest) -> dict:
    """Log a call outcome. Only the outcome category is stored — never content."""
    record_id = f"call_{uuid.uuid4().hex[:12]}"
    record = create_record(
        record_id=record_id,
        campaign_id=body.campaign_id,
        volunteer_id=body.volunteer_id,
        contact_id=body.contact_id,
        outcome=body.outcome,
        duration_seconds=body.duration_seconds,
        notes=body.notes,
    )
    _call_records.append(record)

    # Update engagement on completed calls
    if body.volunteer_id in _volunteers:
        activity = (
            "call_interested"
            if body.outcome == CallOutcome.INTERESTED
            else "call_completed"
        )
        updated = log_activity(_volunteers[body.volunteer_id], activity)
        _volunteers[body.volunteer_id] = updated

    return {"record_id": record_id, "outcome": body.outcome.value}


@app.get("/calls/summary/{campaign_id}")
def call_summary(campaign_id: str) -> dict:
    """Return outcome summary for a campaign."""
    campaign_records = [r for r in _call_records if r.campaign_id == campaign_id]
    return summarise_outcomes(campaign_records)


# ---------------------------------------------------------------------------
# Engagement endpoint
# ---------------------------------------------------------------------------

@app.get("/engagement/at-risk")
def get_at_risk_volunteers() -> list[dict]:
    """Return volunteers who need reactivation outreach."""
    volunteers = list(_volunteers.values())
    at_risk = at_risk_volunteers(volunteers)
    return [
        {
            "volunteer_id": v.volunteer_id,
            "org_id": v.org_id,
            "engagement_score": v.engagement_score,
            "last_active": v.last_active.isoformat() if v.last_active else None,
        }
        for v in at_risk
    ]


# ---------------------------------------------------------------------------
# Coalition broadcast endpoint
# ---------------------------------------------------------------------------

@app.post("/broadcast", status_code=status.HTTP_201_CREATED)
def coalition_broadcast(body: BroadcastRequest) -> dict:
    """Broadcast a dispatch request to all specified coalition orgs.

    Returns per-org match counts only. Individual volunteer data never crosses
    org boundaries.
    """
    request = DispatchRequest(
        request_id=f"req_{uuid.uuid4().hex[:12]}",
        campaign_id=body.campaign_id,
        required_skills=body.required_skills,
        required_languages=body.required_languages,
        urgency=body.urgency,
        description=body.description,
        location_hint=None,
        max_volunteers=10,
    )

    # Build per-org pools from the registered volunteer store
    pools = []
    for org_id in body.org_ids:
        org_volunteers = [v for v in _volunteers.values() if v.org_id == org_id]
        pools.append(OrgVolunteerPool(org_id=org_id, volunteers=org_volunteers))

    broadcast_response = _broadcaster.broadcast(request, pools)

    return {
        "request_id": broadcast_response.request_id,
        "campaign_id": broadcast_response.campaign_id,
        "total_available": broadcast_response.total_available,
        "responding_orgs": broadcast_response.responding_orgs,
        "org_coverage": [
            {
                "org_id": c.org_id,
                "matched_count": c.matched_count,
                "top_match_score": c.top_match_score,
            }
            for c in broadcast_response.org_coverage
        ],
    }
