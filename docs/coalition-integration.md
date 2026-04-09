# Coalition Integration Guide

## Overview

open-paws-volunteer supports multi-org coalition dispatch. Partner organizations
can receive and respond to dispatch requests without exposing their volunteer
lists to other coalition members.

## How Data Stays Isolated

Each coalition org operates an independent volunteer pool (`OrgVolunteerPool`).
When a broadcast is sent (`POST /broadcast`), the `CoalitionBroadcaster` runs
matching against each org's pool separately and returns only **coverage counts**
— not individual volunteer IDs or names.

```
Org A volunteers   ──┐
Org B volunteers   ──┼── CoalitionBroadcaster ──> BroadcastResponse
Org C volunteers   ──┘                              (counts only)
```

The `BroadcastResponse` contains:

```json
{
  "org_coverage": [
    {"org_id": "org-a", "matched_count": 3, "top_match_score": 0.85},
    {"org_id": "org-b", "matched_count": 1, "top_match_score": 0.60},
    {"org_id": "org-c", "matched_count": 0, "top_match_score": null}
  ]
}
```

Volunteer identities never cross org boundaries.

## Data Sharing Rules

Coalition data sharing applies the strictest partner's handling rules
(per `closed-decisions.md` coalition data policy). If any partner org
requires zero-retention handling of their volunteer data, all dispatch
operations involving that org must use the zero-retention API path.

## XP Sync to open-paws-platform

Guild XP flows from this service to the platform via Gary MCP:

1. A volunteer completes a dispatch or call
2. `src/engagement/xp.py XPAwarder.award()` creates an `XPAward` record
3. `XPAwarder.sync_to_platform(award)` calls Gary MCP tool `platform_award_xp`
4. The platform Guild ledger records the award under the volunteer's pseudonymous ID

The MCP wire is currently stubbed in `sync_to_platform()`. To activate:
replace the stub with a call to the Gary MCP server running alongside
the open-paws-platform deployment.

### XP Table

| Activity | XP |
|---|---|
| dispatch_accepted | 50 |
| dispatch_completed | 150 |
| call_completed | 30 |
| call_interested | 75 |
| hours_logged_1 | 100 |
| first_dispatch (one-time) | 200 |
| ten_calls (milestone) | 500 |
| hundred_hours (milestone) | 2000 |

## Broadcast Workflow

1. Coordinator creates a `BroadcastRequest` via `POST /broadcast`
2. Request is dispatched to all `org_ids` listed in the payload
3. Each org's coordinator sees the request and confirms acceptance via `POST /dispatch/{id}/accept`
4. `BroadcastResponse.responding_orgs` shows how many orgs have matched volunteers

## Phone Banking Integration

Phone banking campaigns reference volunteers by `volunteer_id` (pseudonymous).
Call outcomes are stored without content — only the outcome category
(answer / no-answer / interested / declined / left-voicemail).

To start a phone banking campaign:

```bash
python -m src.phone_banking.campaign_runner --campaign my-campaign.json
```

Campaign JSON schema:
```json
{
  "campaign_id": "restaurant-outreach-2026-q2",
  "campaign_brief": "Ask restaurants to add plant-based options to their menus.",
  "target_type": "RESTAURANT",
  "tone": "CONVERSATIONAL",
  "contacts": [
    {"contact_id": "rest-001", "display_name": "Green Garden Bistro"}
  ]
}
```

## Privacy Commitments

- **Volunteer location**: used only for proximity matching approximation, never stored
- **Call records**: outcome category only — no conversation content, no transcript
- **Cultural context** (thank-you letters): used only for message personalization, not profiling
- **Pseudonymous IDs**: volunteer_id is never a real name or email address
- **Real deletion**: `DELETE /volunteers/{id}` performs hard deletion, not soft delete

## Running Locally

```bash
# API server
uvicorn src.api.server:app --reload

# Dashboard
streamlit run dashboard/app.py

# Phone banking campaign (dry run)
python -m src.phone_banking.campaign_runner --campaign campaign.json --dry-run
```
