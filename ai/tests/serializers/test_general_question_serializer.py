"""Tests for the GeneralQuestionInputSerializer."""

import pytest
from pydantic import ValidationError

from ai.serializers.general_question import GeneralQuestionInputSerializer


def _valid_payload(**overrides):
    """Build a minimally valid payload, applying any field overrides."""
    payload = {
        "query": "Who is Jesus Christ?",
        "collection_name": "bsb",
    }
    payload.update(overrides)
    return payload


class TestGeneralQuestionInputSerializer:
    """Tests for the GeneralQuestionInputSerializer."""

    def test_valid_payload(self):
        """A fully valid payload should instantiate successfully."""
        serializer = GeneralQuestionInputSerializer(**_valid_payload())

        assert serializer.query == "Who is Jesus Christ?"
        assert serializer.collection_name == "bsb"

    def test_query_strips_surrounding_whitespace(self):
        """query should be returned trimmed of surrounding whitespace."""
        serializer = GeneralQuestionInputSerializer(**_valid_payload(query="  Who is Jesus?  "))

        assert serializer.query == "Who is Jesus?"

    def test_query_empty_raises(self):
        """An empty query should raise ValidationError."""
        with pytest.raises(ValidationError):
            GeneralQuestionInputSerializer(**_valid_payload(query=""))

    def test_query_whitespace_only_raises(self):
        """A whitespace-only query should raise ValidationError."""
        with pytest.raises(ValidationError):
            GeneralQuestionInputSerializer(**_valid_payload(query="   \n\t  "))

    def test_collection_name_max_three_chars_allowed(self):
        """A 3-character collection_name should be accepted (boundary case)."""
        serializer = GeneralQuestionInputSerializer(**_valid_payload(collection_name="bsb"))

        assert serializer.collection_name == "bsb"

    def test_collection_name_exceeding_three_chars_raises(self):
        """A collection_name longer than 3 characters should raise ValidationError."""
        with pytest.raises(ValidationError):
            GeneralQuestionInputSerializer(**_valid_payload(collection_name="bsb_v2"))

    def test_missing_query_raises(self):
        """Omitting the required query field should raise ValidationError."""
        payload = _valid_payload()
        del payload["query"]
        with pytest.raises(ValidationError):
            GeneralQuestionInputSerializer(**payload)

    def test_missing_collection_name_raises(self):
        """Omitting the required collection_name field should raise ValidationError."""
        payload = _valid_payload()
        del payload["collection_name"]
        with pytest.raises(ValidationError):
            GeneralQuestionInputSerializer(**payload)
