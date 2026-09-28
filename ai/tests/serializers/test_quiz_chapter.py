"""Tests for the QuizChapterInputSerializer."""

import pytest
from pydantic import ValidationError

from ai.serializers.quiz_chapter import QuizChapterInputSerializer


def _valid_payload(**overrides):
    payload = {
        "book": "Genesis",
        "chapter": "1",
        "collection_name": "bsb",
    }
    payload.update(overrides)
    return payload


class TestQuizChapterInputSerializer:
    def test_valid_payload(self):
        serializer = QuizChapterInputSerializer(**_valid_payload())

        assert serializer.book == "Genesis"
        assert serializer.chapter == "1"
        assert serializer.collection_name == "bsb"

    @pytest.mark.parametrize("field", ["book", "chapter"])
    @pytest.mark.parametrize("value", ["", "   ", "\t\n"])
    def test_book_and_chapter_reject_blank_values(self, field, value):
        with pytest.raises(ValidationError):
            QuizChapterInputSerializer(**_valid_payload(**{field: value}))

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("  Genesis  ", "Genesis"), ("\t1\n", "1")],
    )
    def test_book_and_chapter_are_trimmed(self, value, expected):
        field = "book" if expected == "Genesis" else "chapter"
        serializer = QuizChapterInputSerializer(**_valid_payload(**{field: value}))

        assert getattr(serializer, field) == expected

    @pytest.mark.parametrize("value", ["", "a", "abc"])
    def test_collection_name_accepts_values_up_to_three_characters(self, value):
        serializer = QuizChapterInputSerializer(**_valid_payload(collection_name=value))

        assert serializer.collection_name == value

    def test_collection_name_longer_than_three_characters_is_rejected(self):
        with pytest.raises(ValidationError, match="max 3 chars"):
            QuizChapterInputSerializer(**_valid_payload(collection_name="bsb_v2"))

    @pytest.mark.parametrize("field", ["book", "chapter", "collection_name"])
    def test_required_fields_cannot_be_omitted(self, field):
        payload = _valid_payload()
        del payload[field]

        with pytest.raises(ValidationError):
            QuizChapterInputSerializer(**payload)
