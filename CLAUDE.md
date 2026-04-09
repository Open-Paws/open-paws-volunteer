# open-paws-volunteer — Agent Instructions

Volunteer coordination platform for animal advocacy coalitions.
Skill-matched dispatch, phone banking, coalition broadcast, XP integration.

## Architecture
- `src/dispatch/` — Skill-matched volunteer routing (Volunteer-Dispatch-Optimizer patterns)
- `src/engagement/` — Engagement decay detection + XP awards (Adventurers-Guild patterns)
- `src/phone_banking/` — Phone banking campaign runner with AI scripts (vegancall patterns)
- `src/coalition/` — Cross-org volunteer dispatch broadcast (per-org data isolation)
- `src/api/` — FastAPI server (`uvicorn src.api.server:app --reload`)
- `dashboard/` — Streamlit coordination dashboard (`streamlit run dashboard/app.py`)

## Integration with open-paws-platform
Guild XP awards via `src/engagement/xp.py`:
- Volunteer hours → XP
- Completed calls → XP
- Dispatch acceptance → XP
- Awards sync to platform via Gary MCP server (`platform_award_xp` tool)
- Sync is currently stubbed in `XPAwarder.sync_to_platform()` — wire when platform MCP is live

## Domain Language
- "activist" or "volunteer" (both valid in this context)
- "campaign" not "project"
- "coalition" for multi-org dispatch
- "dispatch" for assigning volunteers to needs
- "sanctuary" for permanent care facilities (never "shelter")
- "farmed animal" not "livestock"
- "factory farm" not "farm"
- "slaughterhouse" not "abattoir"

## Privacy Rules
- Volunteer location: used only for proximity matching, never stored long-term
- Call records: outcome only (answer/no-answer/interested/declined/left-voicemail), never conversation content
- Cultural context for thank-you letters: used only for personalization, not profiling
- All volunteer IDs are pseudonymous — never store real names in this service

## Bounded Context
This service is the **Coalition Coordination** bounded context.
Data from Investigation Operations must never flow directly into this service.
Any cross-context data requires an explicit anti-corruption layer with auditable translation.

## Scoring (dispatch/matcher.py)
- 60% skill coverage
- 20% language match
- 20% engagement bonus (volunteer.engagement_score * 0.2)
Volunteers with zero skill coverage are excluded from results entirely.

## Engagement Decay (engagement/tracker.py)
- Score starts at 1.0 on first activity
- Decays 0.1/week of inactivity
- Floor: 0.1 (never reaches zero)
- At-risk threshold: 0.3 → triggers reactivation outreach

## XP Table (engagement/xp.py)
dispatch_accepted=50, dispatch_completed=150, call_completed=30,
call_interested=75, hours_logged_1=100, first_dispatch=200 (one-time),
ten_calls=500 (milestone), hundred_hours=2000 (milestone)

## Running
```bash
uvicorn src.api.server:app --reload
streamlit run dashboard/app.py
python -m src.phone_banking.campaign_runner --campaign campaign.json
python -m pytest tests/
```

## Key Open Issues
- Wire XP sync to open-paws-platform Guild via Gary MCP
- Add proximity matching when volunteers share location (haversine is implemented in dispatch/router.py)
- Replace in-memory stores in api/server.py with sqlite-utils persistence
- SMS/WhatsApp notification for dispatch alerts (cc-connect patterns)

## Every Session

Read the strategy repo for current priorities before acting:

```bash
gh api repos/Open-Paws/open-paws-strategy/contents/priorities.md --jq '.content' | base64 -d
gh api repos/Open-Paws/open-paws-strategy/contents/closed-decisions.md --jq '.content' | base64 -d
```

## Quality Gates

Run before every PR:

```bash
pip install "git+https://github.com/Open-Paws/desloppify.git#egg=desloppify[full]"
desloppify scan --path .
desloppify next
```

Minimum passing score: ≥85

Speciesist language scan:
```bash
semgrep --config semgrep-no-animal-violence.yaml .
```

All PRs must pass CI before merge.