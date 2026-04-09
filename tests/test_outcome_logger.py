"""
Tests for call outcome logger.
"""
import pytest
from src.phone_banking.outcome_logger import (
    CallOutcome,
    create_record,
    interested_contacts,
    summarise_outcomes,
)


class TestOutcomeLogger:
    def test_create_record_valid(self):
        """create_record must produce a CallRecord with correct fields."""
        record = create_record(
            record_id="call-001",
            campaign_id="camp-001",
            volunteer_id="vol-001",
            contact_id="contact-001",
            outcome=CallOutcome.INTERESTED,
            duration_seconds=45,
        )
        assert record.record_id == "call-001"
        assert record.outcome == CallOutcome.INTERESTED
        assert record.duration_seconds == 45

    def test_negative_duration_raises(self):
        """Negative duration must raise ValueError — invalid data must not be stored."""
        with pytest.raises(ValueError):
            create_record(
                record_id="r",
                campaign_id="c",
                volunteer_id="v",
                contact_id="ct",
                outcome=CallOutcome.ANSWER,
                duration_seconds=-1,
            )

    def test_summarise_includes_all_outcomes(self):
        """summarise_outcomes must include every outcome key, even with zero counts."""
        records = [
            create_record("r1", "c1", "v1", "ct1", CallOutcome.ANSWER),
            create_record("r2", "c1", "v1", "ct2", CallOutcome.INTERESTED),
        ]
        summary = summarise_outcomes(records)

        for outcome in CallOutcome:
            assert outcome.value in summary, f"{outcome.value} missing from summary"

    def test_summarise_counts_correctly(self):
        """Outcome counts must match the actual records."""
        records = [
            create_record("r1", "c1", "v1", "ct1", CallOutcome.DECLINED),
            create_record("r2", "c1", "v1", "ct2", CallOutcome.DECLINED),
            create_record("r3", "c1", "v1", "ct3", CallOutcome.INTERESTED),
        ]
        summary = summarise_outcomes(records)

        assert summary[CallOutcome.DECLINED.value] == 2
        assert summary[CallOutcome.INTERESTED.value] == 1

    def test_interested_contacts_filters_correctly(self):
        """interested_contacts must return only INTERESTED contact IDs."""
        records = [
            create_record("r1", "c1", "v1", "ct-a", CallOutcome.INTERESTED),
            create_record("r2", "c1", "v1", "ct-b", CallOutcome.DECLINED),
            create_record("r3", "c1", "v1", "ct-c", CallOutcome.INTERESTED),
        ]
        result = interested_contacts(records)

        assert "ct-a" in result
        assert "ct-c" in result
        assert "ct-b" not in result
        assert len(result) == 2
