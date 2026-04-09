"""
AI call script generator for phone banking campaigns.

Adapted from vegancall-v01's approach to AI-assisted restaurant outreach.
Extended to support legislators, corporate switchboards, and coalition targets.

Scripts are generated fresh per campaign brief. The system prompt is static
and placed first in the API call for cache optimization (Anthropic prompt caching).

Privacy: no personally identifiable information about the caller is included
in scripts. Scripts are campaign-level, not caller-specific.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import anthropic


class TargetType(str, Enum):
    RESTAURANT = "RESTAURANT"            # Plant-based menu expansion outreach
    LEGISLATOR = "LEGISLATOR"            # Legislative action / policy call
    CORPORATE = "CORPORATE"              # Corporate policy reform
    MEDIA = "MEDIA"                      # Press / journalist outreach
    COALITION_PARTNER = "COALITION_PARTNER"  # Cross-org coordination call


class ScriptTone(str, Enum):
    CONVERSATIONAL = "CONVERSATIONAL"    # Warm, peer-to-peer
    PROFESSIONAL = "PROFESSIONAL"        # Formal, policy-focused
    URGENT = "URGENT"                    # Time-sensitive action needed


@dataclass(frozen=True)
class CallScript:
    target_type: TargetType
    tone: ScriptTone
    opening: str
    talking_points: list[str]
    objection_responses: dict[str, str]
    voicemail: str
    closing_ask: str
    outcome_options: list[str]  # What the caller should record as outcome


# Static system prompt — never changes per campaign, maximises cache hits.
_SYSTEM_PROMPT = """You write concise, effective phone banking scripts for animal advocacy campaigns.

Rules:
- Never use speciesist idioms or language that normalises harm to animals.
- Scripts are for human callers, not automated systems — keep them natural.
- Opening: under 30 words. Get to the point.
- Talking points: 3–5 bullet points, each one sentence.
- Objection responses: brief, non-combative, empathetic.
- Voicemail: 20–25 seconds when read aloud (approx. 60–70 words).
- Closing ask: one clear, specific request.
- Outcome options: answer / no-answer / interested / declined / left-voicemail.

Format your response as valid JSON matching this structure:
{
  "opening": "...",
  "talking_points": ["...", "..."],
  "objection_responses": {"<objection>": "<response>"},
  "voicemail": "...",
  "closing_ask": "...",
  "outcome_options": ["answer", "no-answer", "interested", "declined", "left-voicemail"]
}"""


def generate_script(
    target_type: TargetType,
    campaign_brief: str,
    tone: ScriptTone = ScriptTone.CONVERSATIONAL,
    *,
    client: Optional[anthropic.Anthropic] = None,
) -> CallScript:
    """Generate a phone banking script for a campaign.

    Args:
        target_type: Who the caller is contacting.
        campaign_brief: 1–3 sentences describing the campaign goal.
        tone: Communication register for the call.
        client: Anthropic client (injected for testing).

    Returns:
        CallScript with all sections populated.
    """
    if client is None:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_message = (
        f"Generate a phone banking script for this campaign:\n\n"
        f"Target: {target_type.value}\n"
        f"Tone: {tone.value}\n"
        f"Brief: {campaign_brief}\n"
    )

    response = client.messages.create(
        model="claude-haiku-4-5",   # Cheapest model capable of structured output
        max_tokens=800,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    return _parse_script(raw, target_type, tone)


def _parse_script(raw: str, target_type: TargetType, tone: ScriptTone) -> CallScript:
    """Parse the LLM JSON response into a CallScript."""
    import json

    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(cleaned.splitlines()[1:])
    if cleaned.endswith("```"):
        cleaned = "\n".join(cleaned.splitlines()[:-1])
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Return a safe fallback rather than crashing mid-campaign
        data = _fallback_script_data(target_type)

    return CallScript(
        target_type=target_type,
        tone=tone,
        opening=data.get("opening", "Hello, I'm calling about animal welfare."),
        talking_points=data.get("talking_points", []),
        objection_responses=data.get("objection_responses", {}),
        voicemail=data.get("voicemail", ""),
        closing_ask=data.get("closing_ask", "Would you be open to a follow-up?"),
        outcome_options=data.get(
            "outcome_options",
            ["answer", "no-answer", "interested", "declined", "left-voicemail"],
        ),
    )


def _fallback_script_data(target_type: TargetType) -> dict:
    """Minimal safe fallback when LLM returns unparseable output."""
    return {
        "opening": "Hello, I'm a volunteer calling about animal advocacy.",
        "talking_points": [
            "Animals in factory farms suffer in conditions the public doesn't see.",
            "Your action today can make a direct difference.",
            "Thousands of people in your area support this cause.",
        ],
        "objection_responses": {
            "Not interested": "I understand. Thank you for your time.",
            "Too busy": "Of course — would a different time work better?",
        },
        "voicemail": (
            "Hi, this is a volunteer with Open Paws. I'm calling about animal welfare "
            "in your community. Please call us back at your convenience — we'd love "
            "to share what we're working on. Thank you."
        ),
        "closing_ask": "Would you be willing to support this campaign?",
        "outcome_options": ["answer", "no-answer", "interested", "declined", "left-voicemail"],
    }
