"""
Tests for skill_tagger.

Each assertion encodes a domain rule: if the behavior breaks, the test must fail.
"""
import pytest

from src.dispatch.models import SkillArea
from src.dispatch.skill_tagger import tag_skills


# ---------------------------------------------------------------------------
# Single-skill descriptions — each must surface the expected area in top 3
# ---------------------------------------------------------------------------

def test_legal_description_tags_legal():
    result = tag_skills("We need an attorney to review our litigation strategy and contract clauses")
    top_areas = [area for area, _ in result[:3]]
    assert SkillArea.LEGAL in top_areas


def test_technical_description_tags_technical():
    result = tag_skills("Build a database and write code to automate evidence collection pipelines")
    top_areas = [area for area, _ in result[:3]]
    assert SkillArea.TECHNICAL in top_areas


def test_investigation_description_tags_investigation():
    result = tag_skills("Document conditions covertly with footage and photographic evidence from the field")
    top_areas = [area for area, _ in result[:3]]
    assert SkillArea.INVESTIGATION in top_areas


def test_communications_description_tags_communications():
    result = tag_skills("Write press releases and media articles for the campaign outreach")
    top_areas = [area for area, _ in result[:3]]
    assert SkillArea.COMMUNICATIONS in top_areas


def test_translation_description_tags_translation():
    result = tag_skills("Translate outreach materials into Spanish and French for bilingual communities")
    top_areas = [area for area, _ in result[:3]]
    assert SkillArea.TRANSLATION in top_areas


def test_medical_description_tags_medical():
    result = tag_skills("Provide veterinary triage and medical care for rescued animals at the clinic")
    top_areas = [area for area, _ in result[:3]]
    assert SkillArea.MEDICAL in top_areas


def test_direct_action_description_tags_direct_action():
    result = tag_skills("Attend the protest demonstration and hold banners at the rally on the street")
    top_areas = [area for area, _ in result[:3]]
    assert SkillArea.DIRECT_ACTION in top_areas


def test_phone_banking_description_tags_phone_banking():
    result = tag_skills("Make phone calls to supporters and log outcomes from each call with the script")
    top_areas = [area for area, _ in result[:3]]
    assert SkillArea.PHONE_BANKING in top_areas


# ---------------------------------------------------------------------------
# Structural invariants
# ---------------------------------------------------------------------------

def test_scores_between_zero_and_one():
    result = tag_skills("legal investigation technical documentation media communications")
    for _, score in result:
        assert 0.0 <= score <= 1.0


def test_results_ranked_descending():
    result = tag_skills("legal attorney litigation court contract law rights")
    scores = [score for _, score in result]
    assert scores == sorted(scores, reverse=True)


def test_empty_description_returns_empty():
    assert tag_skills("") == []


def test_whitespace_only_returns_empty():
    assert tag_skills("   \t\n  ") == []


def test_min_score_filters_noise():
    # A description with no skill-relevant terms should return nothing at a strict threshold
    result = tag_skills("the event is scheduled for next Tuesday afternoon", min_score=0.2)
    assert len(result) == 0


def test_multi_skill_description_returns_multiple_tags():
    result = tag_skills(
        "We need legal review of contracts, technical data analysis, "
        "and media communications for this investigation"
    )
    areas = [area for area, _ in result]
    assert len(areas) >= 3


def test_legal_scores_highest_for_legal_heavy_description():
    result = tag_skills("attorney contract litigation court law legal rights regulation statute")
    assert result[0][0] == SkillArea.LEGAL


def test_technical_scores_highest_for_technical_heavy_description():
    result = tag_skills("code software database engineering api backend developer programming script")
    assert result[0][0] == SkillArea.TECHNICAL
