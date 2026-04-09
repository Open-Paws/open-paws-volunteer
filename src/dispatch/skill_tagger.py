"""
Skill tagger: label free-text task descriptions with SkillArea values.

Pure-Python implementation using keyword expansion and cosine similarity.
No external model downloads, no network calls — safe for high-risk contexts
where advocate device seizure or traffic interception is a real threat model.
"""
import math
import re
from collections import Counter

from .models import SkillArea

# Keyword corpus for each skill area.
# Lower-cased; multi-word phrases are tokenised into constituent words.
_SKILL_KEYWORDS: dict[SkillArea, list[str]] = {
    SkillArea.LEGAL: [
        "legal", "law", "attorney", "lawyer", "contract", "clause",
        "litigation", "court", "compliance", "regulation", "ordinance",
        "statute", "counsel", "advocate", "rights", "policy", "legislation",
        "injunction", "subpoena", "brief", "filing", "deposition",
        "liability", "tort", "appeal", "settlement", "jurisdiction",
    ],
    SkillArea.INVESTIGATION: [
        "investigation", "investigate", "document", "evidence",
        "footage", "covert", "undercover", "surveillance", "field",
        "inspection", "audit", "reconnaissance", "photograph",
        "video", "record", "observe", "monitor", "trace",
        "fact-finding", "exposure", "whistleblower", "witness",
        "document", "collect", "gather", "report", "scene",
    ],
    SkillArea.TECHNICAL: [
        "technical", "software", "code", "coding", "programming", "developer",
        "data", "database", "infrastructure", "devops", "security", "cyber",
        "api", "backend", "frontend", "engineering", "system", "network",
        "automation", "script", "analysis", "analytics", "machine", "learning",
        "artificial", "intelligence", "cloud", "server", "pipeline",
        "deployment", "build", "architecture", "design",
    ],
    SkillArea.COMMUNICATIONS: [
        "communications", "writing", "writer", "media", "press", "pr",
        "public", "relations", "journalist", "journalism", "article", "blog",
        "content", "copywriting", "marketing", "social", "campaign",
        "narrative", "story", "message", "outreach", "spokesperson",
        "interview", "editor", "editing", "publish", "copy", "comms",
        "newsletter", "announcement", "release",
    ],
    SkillArea.DIRECT_ACTION: [
        "direct", "action", "protest", "demonstration", "rally", "march",
        "picket", "blockade", "ground", "presence", "vigil",
        "physical", "person", "banner", "handbill",
        "leafleting", "leaflet", "tabling", "canvassing", "canvass",
        "street", "local", "showing", "appear", "attend",
    ],
    SkillArea.PHONE_BANKING: [
        "phone", "call", "calling", "outreach", "contact", "bank",
        "phonebank", "telephone", "voicemail", "script",
        "conversation", "dial", "dialing", "canvass",
        "supporter", "donor", "follow", "followup", "hotline",
    ],
    SkillArea.TRANSLATION: [
        "translation", "translate", "interpreter", "language", "bilingual",
        "multilingual", "spanish", "french", "hindi", "chinese", "arabic",
        "portuguese", "localize", "localization", "subtitle", "caption",
        "foreign", "international", "interpret",
    ],
    SkillArea.MEDICAL: [
        "medical", "veterinary", "vet", "veterinarian", "animal", "care",
        "health", "rescue", "treatment", "triage", "injury", "wound",
        "surgery", "medication", "prescription", "clinic", "hospital",
        "nursing", "welfare", "diagnosis", "emergency", "first",
        "aid", "trauma",
    ],
}


def _tokenize(text: str) -> list[str]:
    """Lower-case and extract alpha tokens from text."""
    return re.findall(r"[a-z]+", text.lower())


def _build_keyword_vectors(
    skills: dict[SkillArea, list[str]],
) -> dict[SkillArea, Counter]:
    """Pre-compute keyword frequency vectors for each skill area."""
    return {
        area: Counter(
            token for phrase in keywords for token in _tokenize(phrase)
        )
        for area, keywords in skills.items()
    }


_SKILL_VECTORS: dict[SkillArea, Counter] = _build_keyword_vectors(
    _SKILL_KEYWORDS
)


def _cosine(a: Counter, b: Counter) -> float:
    """Cosine similarity between two term-frequency vectors."""
    dot = sum(a[k] * b[k] for k in a if k in b)
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def tag_skills(
    description: str,
    min_score: float = 0.04,
) -> list[tuple[SkillArea, float]]:
    """
    Return SkillArea values ranked by relevance to the task description.

    Uses cosine similarity between the description token frequencies and
    per-skill keyword corpora. All computation is local — no network calls.

    Args:
        description: Free-text task description from the coordinator.
        min_score: Minimum similarity threshold (0–1). Filters noise.

    Returns:
        Ranked list of (SkillArea, score) tuples, highest first.
        Only areas exceeding min_score are included.
    """
    if not description or not description.strip():
        return []

    query = Counter(_tokenize(description))
    scores = [
        (area, _cosine(query, vector))
        for area, vector in _SKILL_VECTORS.items()
    ]
    return sorted(
        [(area, score) for area, score in scores if score >= min_score],
        key=lambda x: x[1],
        reverse=True,
    )
