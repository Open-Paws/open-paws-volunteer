"""
Culturally-adapted thank-you letter generator for volunteers.

Adapted from Thankyouz_C4C (Code 4 Compassion Mumbai hackathon).
Original focused on Indian animal welfare donors; this version extends
the pattern to volunteer recognition across the advocacy coalition.

Trigger conditions (called automatically by engagement tracker):
  - first dispatch completed
  - 100-hour milestone
  - exceptional contribution (coordinator-flagged)

Privacy: cultural context is used only for message personalization.
It is not stored, logged, or used for profiling.

LLM prompt is static and placed first in the API call for cache optimization.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import anthropic

# Static system prompt — placed first so it maximises cache hit rate
# (Anthropic prompt caching: static content before dynamic content).
_SYSTEM_PROMPT = """You write heartfelt, genuine thank-you messages for animal advocacy volunteers.
Your messages are warm, direct, and free of hollow corporate phrasing.
You never use speciesist idioms. You do not use emojis unless the context
explicitly calls for them. You write in plain, accessible language.

When cultural context is provided:
- India / South Asian: acknowledge seva (selfless service) and collective values.
  Use "Dhanyavaad" or "Namaste" only when it fits naturally.
- General / unspecified: warm, universal language about the movement.

Always mention the specific contribution that earned this message.
Keep the message under 300 words."""


@dataclass(frozen=True)
class ThankYouLetter:
    volunteer_id: str
    subject: str
    body: str
    cultural_context: str


def generate(
    volunteer_id: str,
    contribution_summary: str,
    cultural_context: str = "general",
    org_name: str = "Open Paws",
    *,
    client: Optional[anthropic.Anthropic] = None,
) -> ThankYouLetter:
    """Generate a personalized thank-you letter for a volunteer.

    Args:
        volunteer_id: Pseudonymous volunteer ID (not name — privacy).
        contribution_summary: What the volunteer did (e.g. "completed 10 calls
            for the Mercy For Animals restaurant outreach campaign").
        cultural_context: "india", "south_asia", or "general".
        org_name: Organization name to include in the sign-off.
        client: Anthropic client (injected for testing; defaults to env-configured).

    Returns:
        ThankYouLetter with subject and HTML-safe body text.
    """
    if client is None:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_message = (
        f"Write a thank-you message for a volunteer (ID: {volunteer_id}) "
        f"at {org_name}.\n\n"
        f"What they did: {contribution_summary}\n\n"
        f"Cultural context: {cultural_context}\n\n"
        "Provide:\n"
        "SUBJECT: <one-line email subject>\n"
        "BODY: <the full message>\n"
    )

    response = client.messages.create(
        model="claude-haiku-4-5",   # Cheapest capable model for generation tasks
        max_tokens=500,
        system=_SYSTEM_PROMPT,      # Static — cache-optimized
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    subject, body = _parse_response(raw, contribution_summary)

    return ThankYouLetter(
        volunteer_id=volunteer_id,
        subject=subject,
        body=body,
        cultural_context=cultural_context,
    )


def _parse_response(raw: str, fallback_summary: str) -> tuple[str, str]:
    """Extract subject and body from the LLM response."""
    subject = f"Thank you for your contribution to animal advocacy"
    body = raw

    lines = raw.splitlines()
    for i, line in enumerate(lines):
        if line.upper().startswith("SUBJECT:"):
            subject = line.split(":", 1)[1].strip()
        elif line.upper().startswith("BODY:"):
            body = "\n".join(lines[i + 1:]).strip() or line.split(":", 1)[1].strip()
            break

    return subject, body


# Trigger logic — called by the engagement tracker after key milestones

THANK_YOU_TRIGGERS: set[str] = {
    "first_dispatch",
    "hundred_hours",
    "exceptional_contribution",
}
