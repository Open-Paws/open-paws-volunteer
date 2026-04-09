# open-paws-volunteer

Volunteer coordination platform for animal advocacy coalitions.

Skill-matched dispatch, phone banking with AI call scripts, coalition broadcast,
and engagement tracking with Guild XP integration.

## Quick Start

```bash
pip install -e ".[dev]"
uvicorn src.api.server:app --reload
streamlit run dashboard/app.py
```

## Architecture

- `src/dispatch/` — Skill-matched volunteer routing (Volunteer-Dispatch-Optimizer patterns)
- `src/engagement/` — Engagement decay detection + XP awards (Adventurers-Guild patterns)
- `src/phone_banking/` — Phone banking runner with AI scripts (vegancall patterns)
- `src/coalition/` — Cross-org dispatch broadcast with per-org data isolation
- `src/api/` — FastAPI server
- `dashboard/` — Streamlit coordination dashboard
- `docs/` — Coalition integration guide

## Privacy

- Volunteer location: used only for proximity approximation, never stored
- Call records: outcome category only, no content
- Pseudonymous IDs throughout — no real names in API responses

See `docs/coalition-integration.md` for full integration guide.
