"""Tests for the AskSelectedInputSerializer."""

import pytest
from pydantic import ValidationError

from ai.serializers.ask_selected import AskSelectedInputSerializer


def _valid_payload(**overrides):
    """Build a minimally valid payload, applying any field overrides."""
    payload = {
        "selected_text": "For God so loved the world",
        "verses_text": "16) For God so loved the world, that he gave his only begotten Son.",
        "book": "John",
        "chapter": "3",
        "collection_name": "bsb",
        "query": "What does this mean?",
    }
    payload.update(overrides)
    return payload


class TestAskSelectedInputSerializer:
    """Tests for the AskSelectedInputSerializer."""

    def test_valid_payload(self):
        """A fully valid payload should instantiate successfully."""
        serializer = AskSelectedInputSerializer(**_valid_payload())

        assert serializer.selected_text == "For God so loved the world"
        assert serializer.verses_text == "16) For God so loved the world, that he gave his only begotten Son."
        assert serializer.book == "John"
        assert serializer.chapter == "3"
        assert serializer.collection_name == "bsb"
        assert serializer.query == "What does this mean?"

    def test_selected_text_strips_surrounding_whitespace(self):
        """selected_text should be returned trimmed of surrounding whitespace."""
        serializer = AskSelectedInputSerializer(**_valid_payload(selected_text="  For God so loved  "))

        assert serializer.selected_text == "For God so loved"

    def test_selected_text_collapses_blank_lines(self):
        """Blank/whitespace-only lines in selected_text are removed via remove_newlines_whitespace."""
        serializer = AskSelectedInputSerializer(
            **_valid_payload(selected_text="\n\n  For God so loved  \n\n   \nthe world\n")
        )

        assert serializer.selected_text == "For God so loved\nthe world"

    def test_selected_text_empty_raises(self):
        """An empty selected_text should raise ValidationError."""
        with pytest.raises(ValidationError):
            AskSelectedInputSerializer(**_valid_payload(selected_text=""))

    def test_selected_text_whitespace_only_raises(self):
        """A whitespace-only selected_text should raise ValidationError."""
        with pytest.raises(ValidationError):
            AskSelectedInputSerializer(**_valid_payload(selected_text="   \n\t  "))

    def test_verses_text_strips_surrounding_whitespace(self):
        """verses_text should be returned trimmed of surrounding whitespace."""
        serializer = AskSelectedInputSerializer(**_valid_payload(verses_text="  In the beginning  "))

        assert serializer.verses_text == "In the beginning"

    def test_verses_text_empty_raises(self):
        """An empty verses_text should raise ValidationError."""
        with pytest.raises(ValidationError):
            AskSelectedInputSerializer(**_valid_payload(verses_text=""))

    def test_verses_text_whitespace_only_raises(self):
        """A whitespace-only verses_text should raise ValidationError."""
        with pytest.raises(ValidationError):
            AskSelectedInputSerializer(**_valid_payload(verses_text="   \n\t  "))

    def test_book_strips_surrounding_whitespace(self):
        """book should be returned trimmed of surrounding whitespace."""
        serializer = AskSelectedInputSerializer(**_valid_payload(book="  John  "))

        assert serializer.book == "John"

    def test_book_empty_raises(self):
        """An empty book should raise ValidationError."""
        with pytest.raises(ValidationError):
            AskSelectedInputSerializer(**_valid_payload(book=""))

    def test_book_whitespace_only_raises(self):
        """A whitespace-only book should raise ValidationError."""
        with pytest.raises(ValidationError):
            AskSelectedInputSerializer(**_valid_payload(book="   "))

    def test_chapter_strips_surrounding_whitespace(self):
        """chapter should be returned trimmed of surrounding whitespace."""
        serializer = AskSelectedInputSerializer(**_valid_payload(chapter="  3  "))

        assert serializer.chapter == "3"

    def test_chapter_empty_raises(self):
        """An empty chapter should raise ValidationError."""
        with pytest.raises(ValidationError):
            AskSelectedInputSerializer(**_valid_payload(chapter=""))

    def test_chapter_whitespace_only_raises(self):
        """A whitespace-only chapter should raise ValidationError."""
        with pytest.raises(ValidationError):
            AskSelectedInputSerializer(**_valid_payload(chapter="   "))

    def test_collection_name_max_three_chars_allowed(self):
        """A 3-character collection_name should be accepted (boundary case)."""
        serializer = AskSelectedInputSerializer(**_valid_payload(collection_name="bsb"))

        assert serializer.collection_name == "bsb"

    def test_collection_name_exceeding_three_chars_raises(self):
        """A collection_name longer than 3 characters should raise ValidationError."""
        with pytest.raises(ValidationError):
            AskSelectedInputSerializer(**_valid_payload(collection_name="bsb_v2"))

    def test_query_strips_surrounding_whitespace(self):
        """query should be returned trimmed of surrounding whitespace."""
        serializer = AskSelectedInputSerializer(**_valid_payload(query="  What does this mean?  "))

        assert serializer.query == "What does this mean?"

    def test_query_empty_raises(self):
        """An empty query should raise ValidationError."""
        with pytest.raises(ValidationError):
            AskSelectedInputSerializer(**_valid_payload(query=""))

    def test_query_whitespace_only_raises(self):
        """A whitespace-only query should raise ValidationError."""
        with pytest.raises(ValidationError):
            AskSelectedInputSerializer(**_valid_payload(query="   \n\t  "))

    def test_missing_required_field_raises(self):
        """Omitting a required field should raise ValidationError."""
        payload = _valid_payload()
        del payload["query"]
        with pytest.raises(ValidationError):
            AskSelectedInputSerializer(**payload)
