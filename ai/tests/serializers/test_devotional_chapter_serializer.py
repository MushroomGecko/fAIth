"""Tests for the DevotionalChapterInputSerializer."""

import pytest
from pydantic import ValidationError

from ai.serializers.devotional_chapter import DevotionalChapterInputSerializer


def _valid_payload(**overrides):
    """Build a minimally valid payload, applying any field overrides."""
    payload = {
        "book": "Genesis",
        "chapter": "1",
        "collection_name": "bsb",
    }
    payload.update(overrides)
    return payload


class TestDevotionalChapterInputSerializer:
    """Tests for the DevotionalChapterInputSerializer."""

    def test_valid_payload(self):
        """A fully valid payload should instantiate successfully."""
        serializer = DevotionalChapterInputSerializer(**_valid_payload())

        assert serializer.book == "Genesis"
        assert serializer.chapter == "1"
        assert serializer.collection_name == "bsb"

    def test_book_strips_surrounding_whitespace(self):
        """book should be returned trimmed of surrounding whitespace."""
        serializer = DevotionalChapterInputSerializer(**_valid_payload(book="  Genesis  "))

        assert serializer.book == "Genesis"

    def test_book_empty_raises(self):
        """An empty book should raise ValidationError."""
        with pytest.raises(ValidationError):
            DevotionalChapterInputSerializer(**_valid_payload(book=""))

    def test_book_whitespace_only_raises(self):
        """A whitespace-only book should raise ValidationError."""
        with pytest.raises(ValidationError):
            DevotionalChapterInputSerializer(**_valid_payload(book="   "))

    def test_chapter_strips_surrounding_whitespace(self):
        """chapter should be returned trimmed of surrounding whitespace."""
        serializer = DevotionalChapterInputSerializer(**_valid_payload(chapter="  1  "))

        assert serializer.chapter == "1"

    def test_chapter_empty_raises(self):
        """An empty chapter should raise ValidationError."""
        with pytest.raises(ValidationError):
            DevotionalChapterInputSerializer(**_valid_payload(chapter=""))

    def test_chapter_whitespace_only_raises(self):
        """A whitespace-only chapter should raise ValidationError."""
        with pytest.raises(ValidationError):
            DevotionalChapterInputSerializer(**_valid_payload(chapter="   "))

    def test_collection_name_max_three_chars_allowed(self):
        """A 3-character collection_name should be accepted (boundary case)."""
        serializer = DevotionalChapterInputSerializer(**_valid_payload(collection_name="bsb"))

        assert serializer.collection_name == "bsb"

    def test_collection_name_exceeding_three_chars_raises(self):
        """A collection_name longer than 3 characters should raise ValidationError."""
        with pytest.raises(ValidationError):
            DevotionalChapterInputSerializer(**_valid_payload(collection_name="bsb_v2"))

    def test_missing_required_field_raises(self):
        """Omitting a required field should raise ValidationError."""
        payload = _valid_payload()
        del payload["book"]
        with pytest.raises(ValidationError):
            DevotionalChapterInputSerializer(**payload)
