"""Tests for the ImageSearchInputSerializer."""

import pytest
from pydantic import ValidationError

from ai.serializers.image_search import ImageSearchInputSerializer


def _valid_payload(**overrides):
    """Build a minimally valid payload, applying any field overrides."""
    payload = {
        "selected_text": "For God so loved the world",
        "verses_text": "16) For God so loved the world, that he gave his only begotten Son.",
        "book": "John",
        "chapter": "3",
        "collection_name": "bsb",
    }
    payload.update(overrides)
    return payload


class TestImageSearchInputSerializer:
    """Tests for the ImageSearchInputSerializer."""

    def test_valid_payload(self):
        """A fully valid payload should instantiate successfully."""
        serializer = ImageSearchInputSerializer(**_valid_payload())

        assert serializer.selected_text == "For God so loved the world"
        assert serializer.book == "John"
        assert serializer.chapter == "3"
        assert serializer.collection_name == "bsb"

    def test_selected_text_strips_surrounding_whitespace(self):
        """selected_text should be returned trimmed of surrounding whitespace."""
        serializer = ImageSearchInputSerializer(**_valid_payload(selected_text="  For God so loved  "))

        assert serializer.selected_text == "For God so loved"

    def test_selected_text_collapses_blank_lines(self):
        """Blank/whitespace-only lines in selected_text are removed via remove_newlines_whitespace."""
        serializer = ImageSearchInputSerializer(
            **_valid_payload(selected_text="\n\n  For God so loved  \n\n   \nthe world\n")
        )

        assert serializer.selected_text == "For God so loved\nthe world"

    def test_selected_text_empty_raises(self):
        """An empty selected_text should raise ValidationError."""
        with pytest.raises(ValidationError):
            ImageSearchInputSerializer(**_valid_payload(selected_text=""))

    def test_selected_text_whitespace_only_raises(self):
        """A whitespace-only selected_text should raise ValidationError."""
        with pytest.raises(ValidationError):
            ImageSearchInputSerializer(**_valid_payload(selected_text="   \n\t  "))

    def test_verses_text_strips_surrounding_whitespace(self):
        """verses_text should be returned trimmed of surrounding whitespace."""
        serializer = ImageSearchInputSerializer(**_valid_payload(verses_text="  In the beginning  "))

        assert serializer.verses_text == "In the beginning"

    def test_verses_text_empty_raises(self):
        """An empty verses_text should raise ValidationError."""
        with pytest.raises(ValidationError):
            ImageSearchInputSerializer(**_valid_payload(verses_text=""))

    def test_verses_text_whitespace_only_raises(self):
        """A whitespace-only verses_text should raise ValidationError."""
        with pytest.raises(ValidationError):
            ImageSearchInputSerializer(**_valid_payload(verses_text="   \n\t  "))

    def test_book_strips_surrounding_whitespace(self):
        """book should be returned trimmed of surrounding whitespace."""
        serializer = ImageSearchInputSerializer(**_valid_payload(book="  John  "))

        assert serializer.book == "John"

    def test_book_empty_raises(self):
        """An empty book should raise ValidationError."""
        with pytest.raises(ValidationError):
            ImageSearchInputSerializer(**_valid_payload(book=""))

    def test_book_whitespace_only_raises(self):
        """A whitespace-only book should raise ValidationError."""
        with pytest.raises(ValidationError):
            ImageSearchInputSerializer(**_valid_payload(book="   "))

    def test_chapter_strips_surrounding_whitespace(self):
        """chapter should be returned trimmed of surrounding whitespace."""
        serializer = ImageSearchInputSerializer(**_valid_payload(chapter="  3  "))

        assert serializer.chapter == "3"

    def test_chapter_empty_raises(self):
        """An empty chapter should raise ValidationError."""
        with pytest.raises(ValidationError):
            ImageSearchInputSerializer(**_valid_payload(chapter=""))

    def test_chapter_whitespace_only_raises(self):
        """A whitespace-only chapter should raise ValidationError."""
        with pytest.raises(ValidationError):
            ImageSearchInputSerializer(**_valid_payload(chapter="   "))

    def test_missing_required_field_raises(self):
        """Omitting a required field should raise ValidationError."""
        payload = _valid_payload()
        del payload["book"]
        with pytest.raises(ValidationError):
            ImageSearchInputSerializer(**payload)
