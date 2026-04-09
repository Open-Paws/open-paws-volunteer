from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from datetime import datetime


class SkillArea(str, Enum):
    LEGAL = "LEGAL"                       # Legal expertise, attorney
    INVESTIGATION = "INVESTIGATION"       # Field investigation experience
    TECHNICAL = "TECHNICAL"              # Software, data, IT
    COMMUNICATIONS = "COMMUNICATIONS"    # Writing, media, PR
    DIRECT_ACTION = "DIRECT_ACTION"      # On-the-ground presence
    PHONE_BANKING = "PHONE_BANKING"      # Outreach calls
    TRANSLATION = "TRANSLATION"          # Language skills
    MEDICAL = "MEDICAL"                  # Veterinary, medical


class AvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class Urgency(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    TODAY = "TODAY"
    THIS_WEEK = "THIS_WEEK"


@dataclass
class Volunteer:
    volunteer_id: str                      # Pseudonymous ID — never real name in transit
    org_id: str                           # Coalition org affiliation
    skills: list[SkillArea]
    languages: list[str]                  # ISO 639-1 codes
    timezone: str                         # IANA timezone
    availability: AvailabilityStatus = AvailabilityStatus.OFFLINE
    total_hours: float = 0.0
    total_xp: int = 0
    last_active: Optional[datetime] = None
    engagement_score: float = 1.0        # 0.0–1.0, decays with inactivity
    total_dispatches: int = 0
    successful_dispatches: int = 0


@dataclass
class DispatchRequest:
    request_id: str
    campaign_id: str
    required_skills: list[SkillArea]
    required_languages: list[str]
    urgency: Urgency
    description: str
    location_hint: Optional[str]         # City/region for proximity approximation
    max_volunteers: int = 1


@dataclass
class DispatchMatch:
    volunteer_id: str
    request_id: str
    match_score: float                   # 0.0–1.0 composite
    skill_coverage: float                # Fraction of required skills covered
    accepted: Optional[bool] = None
    accepted_at: Optional[datetime] = None
