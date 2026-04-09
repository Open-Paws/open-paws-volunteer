# Open Paws Volunteer — Agent Quick Reference

Volunteer dispatch platform with skill-matched assignment, phone banking, coalition broadcast, and engagement XP tracking.

## How to Run

```bash
# Install
pip install -e ".[dev]"

# Start API server
uvicorn src.api.server:app --reload

# Run tests
python -m pytest tests/ -v
```

## Full Agent Routing

See `CLAUDE.md` for complete context: tech stack, key files, strategic role, quality gates, and task routing table.
