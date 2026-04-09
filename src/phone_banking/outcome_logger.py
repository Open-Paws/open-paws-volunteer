"""
Call outcome recording for phone banking campaigns.

Privacy rules (enforced here, not by convention):
  - Only the outcome category is stored — never conversation content.
  - No caller identity in records — only volunteer_id (pseudonymous).
  - Contact information is referenced by contact_id, never stored in this module.

Outcome categories mirror vegancall-v01's state machine:
  answer / no-answer / interested / declined / left-voicemail
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class CallOutcome(str, Enum):
    ANSWER = "answer"
    NO_ANSWER = "no-answer"
    INTERESTED = "interested"          # Target expressed genuine interest
    DECLINED = "declined"
    LEFT_VOICEMAIL = "left-voicemail"


@dataclass(frozen=True)
class CallRecord:
    record_id: str
    campaign_id: str
    volunteer_id: str                  # Pseudonymous
    contact_id: str                    # Reference only — contact data lives elsewhere
    outcome: CallOutcome
    duration_seconds: int              # 0 for no-answer
    notes: Optional[str]               # Brief coordinator notes only — not transcript
    recorded_at: datetime


def create_record(
    record_id: str,
    campaign_id: str,
    volunteer_id: str,
    contact_id: str,
    outcome: CallOutcome,
    duration_seconds: int = 0,
    notes: Optional[str] = None,
) -> CallRecord:
    """Create an immutable call record.

    Raises ValueError if duration is negative or outcome is invalid.
    """
    if duration_seconds < 0:
        raise ValueError(f"duration_seconds cannot be negative, got {duration_seconds}")
    return CallRecord(
        record_id=record_id,
        campaign_id=campaign_id,
        volunteer_id=volunteer_id,
        contact_id=contact_id,
        outcome=outcome,
        duration_seconds=duration_seconds,
        notes=notes,
        recorded_at=datetime.now(tz=timezone.utc),
    )


def summarise_outcomes(records: list[CallRecord]) -> dict[str, int]:
    """Count outcomes across a set of call records.

    Returns a dict mapping outcome name to count, including all defined
    outcomes with zero counts so dashboards don't need to handle missing keys.
    """
    counts: dict[str, int] = {o.value: 0 for o in CallOutcome}
    for r in records:
        counts[r.outcome.value] += 1
    return counts


def interested_contacts(records: list[CallRecord]) -> list[str]:
    """Return contact IDs for targets that expressed interest."""
    return [r.contact_id for r in records if r.outcome == CallOutcome.INTERESTED]
