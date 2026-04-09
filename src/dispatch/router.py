"""
Proximity routing and availability management for volunteer dispatch.

Proximity is approximated via timezone when volunteers have not shared location.
Volunteers who share location (lat/lon) get haversine distance scoring.
Both approaches feed into the same DispatchMatch score produced by VolunteerMatcher.
"""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Optional

from .models import AvailabilityStatus, Volunteer

# Distance score bands adapted from Volunteer-Dispatch-Optimizer scoring.py
# (distance_km, score)
DISTANCE_SCORE_BANDS: tuple[tuple[float, float], ...] = (
    (5.0, 1.0),
    (15.0, 0.90),
    (30.0, 0.75),
    (50.0, 0.60),
    (80.0, 0.40),
    (120.0, 0.20),
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points in kilometres."""
    r = 6371.0
    phi1, lam1, phi2, lam2 = map(radians, [lat1, lon1, lat2, lon2])
    dphi = phi2 - phi1
    dlam = lam2 - lam1
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlam / 2) ** 2
    return r * 2 * asin(sqrt(a))


def distance_score(distance_km: float) -> float:
    """Convert a distance in km to a 0.0–1.0 score."""
    for upper_bound, score in DISTANCE_SCORE_BANDS:
        if distance_km <= upper_bound:
            return score
    return 0.0


def set_availability(volunteer: Volunteer, status: AvailabilityStatus) -> Volunteer:
    """Return a copy of the volunteer with updated availability."""
    from dataclasses import replace
    return replace(volunteer, availability=status)


def filter_by_availability(
    volunteers: list[Volunteer],
    include_busy: bool = False,
) -> list[Volunteer]:
    """Return only volunteers who are currently contactable.

    By default only AVAILABLE volunteers are returned. Pass include_busy=True
    to also include BUSY volunteers (e.g. for IMMEDIATE urgency fallback).
    """
    allowed = {AvailabilityStatus.AVAILABLE}
    if include_busy:
        allowed.add(AvailabilityStatus.BUSY)
    return [v for v in volunteers if v.availability in allowed]
