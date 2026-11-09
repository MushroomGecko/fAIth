"""Tests for the note request serializers."""

import uuid

import pytest
from pydantic import ValidationError

from backend.serializers.note import (
    DeleteNoteInputSerializer,
    NoteInputSerializer,
    UpdateNoteInputSerializer,
)

YELLOW = "#FFFF00"


def _note_data(**overrides):
    data = {
        "collection_name": "bsb",
        "book": "Genesis",
        "chapter": "1",
        "note": "A note",
    }
    data.update(overrides)
    return data


def _highlight_data(**overrides):
    """A note with a valid highlight in verse 16, from character 0 to 5."""
    data = _note_data(
        highlight_coordinates={"16": {"beginning": 0, "end": 5}},
        highlight_color=YELLOW,
    )
    data.update(overrides)
    return data


class TestNoteInputSerializerDefaults:
    """Defaults for a general note with no selection or highlight."""

    def test_general_note_has_empty_selection_and_no_highlight(self):
        """Test that a note with only the required fields gets empty defaults."""
        serializer = NoteInputSerializer(**_note_data())

        assert serializer.selected_html == ""
        assert serializer.verses_text == ""
        assert serializer.highlight_coordinates == {}
        assert serializer.highlight_color is None


class TestNoteInputSerializerRequiredFields:
    """Required text fields must be present, non-empty, and within limits."""

    def test_collection_name_of_three_chars_is_accepted(self):
        """Test that a collection name of exactly 3 characters is allowed."""
        assert NoteInputSerializer(**_note_data(collection_name="bsb")).collection_name == "bsb"

    def test_collection_name_longer_than_three_chars_is_rejected(self):
        """Test that a collection name over 3 characters is rejected."""
        with pytest.raises(ValidationError, match="collection_name must be max 3 chars"):
            NoteInputSerializer(**_note_data(collection_name="bsbx"))

    @pytest.mark.parametrize("field", ["book", "chapter", "note"])
    def test_blank_required_field_is_rejected(self, field):
        """Test that a required field that is only whitespace is rejected."""
        with pytest.raises(ValidationError):
            NoteInputSerializer(**_note_data(**{field: "   "}))

    def test_book_and_chapter_are_trimmed(self):
        """Test that surrounding whitespace is removed from book and chapter."""
        serializer = NoteInputSerializer(**_note_data(book="  Genesis ", chapter=" 1 "))

        assert serializer.book == "Genesis"
        assert serializer.chapter == "1"

    def test_note_is_trimmed(self):
        """Test that surrounding whitespace is removed from the note text."""
        assert NoteInputSerializer(**_note_data(note="  hello  ")).note == "hello"


class TestNoteInputSerializerSelection:
    """Selected HTML and verse text from the browser."""

    def test_selected_html_keeps_spans_and_removes_blank_lines(self):
        """Test that selected HTML keeps its markup, with blank and whitespace-only lines removed."""
        result = NoteInputSerializer(**_note_data(selected_html='<span class="wj">a</span>\n\n   b  \n'))

        assert result.selected_html == '<span class="wj">a</span>\nb'

    def test_verses_text_is_trimmed(self):
        """Test that verses text is stripped of surrounding whitespace."""
        assert NoteInputSerializer(**_note_data(verses_text="  16) For God  ")).verses_text == "16) For God"


class TestNoteInputSerializerHighlightCoordinates:
    """highlight_coordinates: JSON from forms, validated per verse."""

    @pytest.mark.parametrize("blank", ["", "   ", "{}", None])
    def test_blank_coordinates_become_empty_dict(self, blank):
        """Test that blank input, an empty object, or None all mean no highlight."""
        serializer = NoteInputSerializer(**_note_data(highlight_coordinates=blank))

        assert serializer.highlight_coordinates == {}

    def test_json_string_from_form_is_parsed(self):
        """Test that coordinates posted as a JSON string are parsed into a dict."""
        serializer = NoteInputSerializer(**_highlight_data(highlight_coordinates='{"16": {"beginning": 0, "end": 5}}'))

        assert serializer.highlight_coordinates == {"16": {"beginning": 0, "end": 5}}

    def test_invalid_json_is_rejected(self):
        """Test that a coordinates string that isn't valid JSON is rejected."""
        with pytest.raises(ValidationError, match="must be valid JSON"):
            NoteInputSerializer(**_highlight_data(highlight_coordinates="not json"))

    @pytest.mark.parametrize("verse_key", ["0", "-1", "abc", "1.5"])
    def test_verse_key_must_be_a_positive_number(self, verse_key):
        """Test that verse keys must be positive whole numbers."""
        with pytest.raises(ValidationError, match="positive verse numbers"):
            NoteInputSerializer(**_highlight_data(highlight_coordinates={verse_key: {"beginning": 0, "end": 5}}))

    def test_missing_key_is_rejected(self):
        """Test that each verse needs both 'beginning' and 'end'."""
        with pytest.raises(ValidationError, match="exactly 'beginning' and 'end' keys"):
            NoteInputSerializer(**_highlight_data(highlight_coordinates={"16": {"beginning": 0}}))

    def test_extra_key_is_rejected(self):
        """Test that a verse with keys other than 'beginning' and 'end' is rejected."""
        with pytest.raises(ValidationError, match="exactly 'beginning' and 'end' keys"):
            NoteInputSerializer(**_highlight_data(highlight_coordinates={"16": {"beginning": 0, "end": 5, "extra": 1}}))

    def test_negative_beginning_is_rejected(self):
        """Test that a negative start offset is rejected."""
        with pytest.raises(ValidationError, match="non-negative and less than 'end'"):
            NoteInputSerializer(**_highlight_data(highlight_coordinates={"16": {"beginning": -1, "end": 5}}))

    @pytest.mark.parametrize(("beginning", "end"), [(5, 5), (6, 5)])
    def test_end_must_be_after_beginning(self, beginning, end):
        """Test that a zero-length or backwards highlight is rejected."""
        with pytest.raises(ValidationError, match="non-negative and less than 'end'"):
            NoteInputSerializer(**_highlight_data(highlight_coordinates={"16": {"beginning": beginning, "end": end}}))

    def test_non_integer_offset_is_rejected(self):
        """Test that offsets must be whole numbers."""
        with pytest.raises(ValidationError):
            NoteInputSerializer(**_highlight_data(highlight_coordinates={"16": {"beginning": "x", "end": 5}}))

    def test_several_verses_are_accepted(self):
        """Test that a highlight can cover more than one verse."""
        coordinates = {"16": {"beginning": 0, "end": 5}, "17": {"beginning": 3, "end": 9}}

        serializer = NoteInputSerializer(**_highlight_data(highlight_coordinates=coordinates))

        assert serializer.highlight_coordinates == coordinates


class TestNoteInputSerializerHighlightColor:
    """highlight_color: a hex color or nothing."""

    def test_valid_color_is_uppercased(self):
        """Test that a lowercase hex color is converted to uppercase."""
        assert NoteInputSerializer(**_highlight_data(highlight_color="#ffff00")).highlight_color == YELLOW

    def test_surrounding_whitespace_is_removed_from_color(self):
        """Test that spaces around a valid color are removed."""
        assert NoteInputSerializer(**_highlight_data(highlight_color="  #00bfff ")).highlight_color == "#00BFFF"

    @pytest.mark.parametrize("blank", ["", "   ", None])
    def test_blank_color_becomes_none(self, blank):
        """Test that a blank color means no highlight color."""
        assert NoteInputSerializer(**_note_data(highlight_color=blank)).highlight_color is None

    @pytest.mark.parametrize("color", ["#FFF", "red", "FFFF00", "#GGGGGG", "#FFFF000"])
    def test_invalid_color_is_rejected(self, color):
        """Test that anything other than #RRGGBB is rejected."""
        with pytest.raises(ValidationError, match="hex color"):
            NoteInputSerializer(**_highlight_data(highlight_color=color))


class TestNoteInputSerializerHighlightPairing:
    """A color and coordinates must be set together, or both left empty."""

    def test_color_and_coordinates_together_are_accepted(self):
        """Test that a note with both a color and coordinates is valid."""
        serializer = NoteInputSerializer(**_highlight_data())

        assert serializer.highlight_color == YELLOW
        assert serializer.highlight_coordinates == {"16": {"beginning": 0, "end": 5}}

    def test_coordinates_without_color_are_rejected(self):
        """Test that a highlight with no color is rejected."""
        with pytest.raises(ValidationError, match="both be set or both be empty"):
            NoteInputSerializer(**_note_data(highlight_coordinates={"16": {"beginning": 0, "end": 5}}))

    def test_color_without_coordinates_is_rejected(self):
        """Test that a color with no highlight is rejected."""
        with pytest.raises(ValidationError, match="both be set or both be empty"):
            NoteInputSerializer(**_note_data(highlight_color=YELLOW))


class TestUpdateNoteInputSerializer:
    """Updates change the note text and color only, never the coordinates."""

    def test_valid_update_is_accepted(self):
        """Test that an update with a note ID and text is valid, with no color by default."""
        note_id = uuid.uuid4()

        serializer = UpdateNoteInputSerializer(note_id=str(note_id), note="Updated")

        assert serializer.note_id == note_id
        assert serializer.note == "Updated"
        assert serializer.highlight_color is None

    def test_invalid_note_id_is_rejected(self):
        """Test that a note ID that isn't a UUID is rejected."""
        with pytest.raises(ValidationError):
            UpdateNoteInputSerializer(note_id="not-a-uuid", note="Updated")

    def test_blank_note_is_rejected(self):
        """Test that an update with blank text is rejected."""
        with pytest.raises(ValidationError, match="note cannot be empty"):
            UpdateNoteInputSerializer(note_id=str(uuid.uuid4()), note="   ")

    def test_color_is_uppercased(self):
        """Test that the new color is normalized the same way as on create."""
        serializer = UpdateNoteInputSerializer(note_id=str(uuid.uuid4()), note="Updated", highlight_color="#ff69b4")

        assert serializer.highlight_color == "#FF69B4"

    def test_invalid_color_is_rejected(self):
        """Test that an update with an invalid color is rejected."""
        with pytest.raises(ValidationError, match="hex color"):
            UpdateNoteInputSerializer(note_id=str(uuid.uuid4()), note="Updated", highlight_color="pink")

    def test_coordinates_are_not_accepted(self):
        """Test that the update serializer doesn't have a coordinates field, so coordinates are ignored."""
        serializer = UpdateNoteInputSerializer(
            note_id=str(uuid.uuid4()), note="Updated", highlight_coordinates={"16": {"beginning": 0, "end": 5}}
        )

        assert not hasattr(serializer, "highlight_coordinates")


class TestDeleteNoteInputSerializer:
    """Delete requests need a valid note ID."""

    def test_valid_note_id_is_accepted(self):
        """Test that a UUID note ID is accepted."""
        note_id = uuid.uuid4()

        assert DeleteNoteInputSerializer(note_id=str(note_id)).note_id == note_id

    def test_invalid_note_id_is_rejected(self):
        """Test that a note ID that isn't a UUID is rejected."""
        with pytest.raises(ValidationError):
            DeleteNoteInputSerializer(note_id="123")
