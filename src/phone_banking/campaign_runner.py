"""
Phone banking campaign runner.

Loads a contact list, assigns volunteers via VolunteerMatcher,
tracks outcomes per volunteer and per contact, and produces a
campaign progress report.

Usage:
  python -m src.phone_banking.campaign_runner --campaign campaign.json

campaign.json schema:
  {
    "campaign_id": "...",
    "campaign_brief": "...",
    "target_type": "RESTAURANT" | "LEGISLATOR" | ...,
    "tone": "CONVERSATIONAL" | "PROFESSIONAL" | "URGENT",
    "contacts": [{"contact_id": "...", "display_name": "..."}, ...]
  }

Privacy:
  Contact records contain only contact_id and display_name.
  Phone numbers are referenced externally and never written to this module.
  Call content is never recorded — only outcome categories.
"""
from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.dispatch.matcher import VolunteerMatcher
from src.dispatch.models import DispatchRequest, DispatchMatch, SkillArea, Urgency, Volunteer
from src.phone_banking.outcome_logger import (
    CallOutcome,
    CallRecord,
    summarise_outcomes,
)
from src.phone_banking.script_generator import ScriptTone, TargetType, generate_script


@dataclass
class CampaignProgress:
    campaign_id: str
    total_contacts: int
    completed_calls: int
    outcome_summary: dict[str, int]
    interested_count: int
    volunteer_leaderboard: list[dict]  # [{volunteer_id, calls, interested}]


def load_campaign(path: str) -> dict:
    """Load and validate a campaign JSON file."""
    data = json.loads(Path(path).read_text())
    required = {"campaign_id", "campaign_brief", "target_type", "contacts"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Campaign file missing required keys: {missing}")
    return data


def run_campaign(
    campaign: dict,
    volunteers: list[Volunteer],
    records: Optional[list[CallRecord]] = None,
) -> tuple[list[DispatchMatch], CampaignProgress]:
    """Match volunteers to campaign contacts and build a progress report.

    Does not make any actual calls — this is the coordination layer.
    Call execution happens via the phone banking interface (CLI or dashboard).

    Args:
        campaign: Loaded campaign dict.
        volunteers: Available volunteers.
        records: Existing call records for this campaign (for reporting).

    Returns:
        (matches, progress) tuple.
    """
    records = records or []
    matcher = VolunteerMatcher()

    target_type = TargetType(campaign["target_type"])
    tone = ScriptTone(campaign.get("tone", "CONVERSATIONAL"))

    # Build a dispatch request for phone banking skill
    request = DispatchRequest(
        request_id=str(uuid.uuid4()),
        campaign_id=campaign["campaign_id"],
        required_skills=[SkillArea.PHONE_BANKING],
        required_languages=campaign.get("required_languages", []),
        urgency=Urgency(campaign.get("urgency", "THIS_WEEK")),
        description=campaign["campaign_brief"],
        location_hint=campaign.get("location_hint"),
        max_volunteers=campaign.get("max_volunteers", 10),
    )

    matches = matcher.match(request, volunteers, max_results=request.max_volunteers)

    progress = _build_progress(campaign["campaign_id"], campaign["contacts"], records)
    return matches, progress


def _build_progress(
    campaign_id: str,
    contacts: list[dict],
    records: list[CallRecord],
) -> CampaignProgress:
    """Build a CampaignProgress report from existing call records."""
    campaign_records = [r for r in records if r.campaign_id == campaign_id]
    outcome_summary = summarise_outcomes(campaign_records)
    interested_count = outcome_summary.get(CallOutcome.INTERESTED.value, 0)

    # Volunteer leaderboard
    volunteer_stats: dict[str, dict] = {}
    for rec in campaign_records:
        vid = rec.volunteer_id
        if vid not in volunteer_stats:
            volunteer_stats[vid] = {"volunteer_id": vid, "calls": 0, "interested": 0}
        volunteer_stats[vid]["calls"] += 1
        if rec.outcome == CallOutcome.INTERESTED:
            volunteer_stats[vid]["interested"] += 1

    leaderboard = sorted(
        volunteer_stats.values(), key=lambda x: x["interested"], reverse=True
    )

    return CampaignProgress(
        campaign_id=campaign_id,
        total_contacts=len(contacts),
        completed_calls=len(campaign_records),
        outcome_summary=outcome_summary,
        interested_count=interested_count,
        volunteer_leaderboard=leaderboard,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Phone banking campaign runner")
    parser.add_argument("--campaign", required=True, help="Path to campaign JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Print script only, no matching")
    args = parser.parse_args()

    campaign = load_campaign(args.campaign)
    target_type = TargetType(campaign["target_type"])
    tone = ScriptTone(campaign.get("tone", "CONVERSATIONAL"))

    script = generate_script(target_type, campaign["campaign_brief"], tone)

    print(f"\n=== Campaign: {campaign['campaign_id']} ===")
    print(f"Contacts: {len(campaign['contacts'])}")
    print(f"\n-- Call Script ({target_type.value} / {tone.value}) --")
    print(f"Opening: {script.opening}")
    print("Talking points:")
    for point in script.talking_points:
        print(f"  - {point}")
    print(f"Closing ask: {script.closing_ask}")
    print(f"Voicemail: {script.voicemail}")

    if args.dry_run:
        return

    print("\nLoad volunteers from your data source and call run_campaign() to proceed.")


if __name__ == "__main__":
    main()
