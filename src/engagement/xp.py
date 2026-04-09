"""
XP awards for volunteer activities.

Integrates with open-paws-platform Guild system via Gary MCP.
XP table values are calibrated to the platform Guild schema — do not change
them without coordinating with the platform team.

Sync flow:
  1. award() produces an XPAward record
  2. sync_to_platform() is called immediately after award
  3. Gary MCP tool `platform_award_xp` writes to the platform Guild ledger
  4. Until the MCP wire is live, sync returns True (optimistic, no-op)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class XPAward:
    volunteer_id: str
    activity: str
    xp_amount: int
    reason: str


# XP table — values must match platform Guild schema.
# Milestones (first_dispatch, ten_calls, hundred_hours) are one-time awards
# checked by the caller before invoking award().
XP_TABLE: dict[str, int] = {
    "dispatch_accepted": 50,
    "dispatch_completed": 150,
    "call_completed": 30,
    "call_interested": 75,        # Target expressed interest in the campaign
    "hours_logged_1": 100,        # Per hour logged
    "first_dispatch": 200,        # One-time bonus: first ever dispatch accepted
    "ten_calls": 500,             # Milestone: 10 calls completed
    "hundred_hours": 2000,        # Milestone: 100 total hours
}


class XPAwarder:
    """Issue XP awards for volunteer activities and sync to the platform Guild."""

    def award(self, volunteer_id: str, activity: str) -> XPAward:
        """Create an XPAward for the given activity.

        Raises ValueError for unknown activity keys so callers cannot silently
        award zero XP due to typos.
        """
        if activity not in XP_TABLE:
            raise ValueError(
                f"Unknown XP activity: {activity!r}. "
                f"Valid keys: {sorted(XP_TABLE)}"
            )
        amount = XP_TABLE[activity]
        return XPAward(
            volunteer_id=volunteer_id,
            activity=activity,
            xp_amount=amount,
            reason=f"Awarded {amount} XP for: {activity}",
        )

    def sync_to_platform(self, award: XPAward) -> bool:
        """Sync an XP award to open-paws-platform via Gary MCP.

        Returns True if the sync succeeded, False on failure.
        Currently stubbed — wire to Gary MCP tool `platform_award_xp` when live.

        The stub is intentionally optimistic (returns True) so that
        award logic can be tested end-to-end before the platform MCP is available.
        TODO: call Gary MCP `platform_award_xp` with award fields.
        """
        return True
