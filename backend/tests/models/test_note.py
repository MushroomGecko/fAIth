"""Tests for the Note model in backend.models.note.

Most classes here don't touch the database. SimpleTestCase blocks database access, so a test there can't save a note
by accident. TestNoteDatabase saves and reloads notes in the in-memory SQLite test database, which checks that the
fields round-trip through the database.
"""

from cryptography.fernet import InvalidToken
from django.core.exceptions import ValidationError
from django.db import models
from django.test import SimpleTestCase, TestCase

from backend.models.note import Note, parse_verses_numbers
from backend.models.user import User


def _make_note(**overrides):
    fields = {
        "user": User(username="note-model-user"),
        "collection_name": "bsb",
        "book": "Genesis",
        "chapter": 1,
        "verses_text": "16) For God so loved the world",
        "selected_html": "For God so loved the world",
        "verses_numbers": [16],
    }
    fields.update(overrides)
    return Note(**fields)


class TestNoteEncryptedText(SimpleTestCase):
    """The note text is stored encrypted in encrypted_note and read back with decrypted_note."""

    def test_set_note_stores_encrypted_text_not_plain_text(self):
        """Test that the note text is stored encrypted, not as typed."""
        note = _make_note()

        note.set_note("My private thought")

        assert note.encrypted_note != "My private thought"
        assert "My private thought" not in note.encrypted_note

    def test_decrypted_note_returns_the_text_as_written(self):
        """Test that decrypted_note returns the text that was set, including unicode."""
        note = _make_note()

        note.set_note("Grace & peace — “amen”")

        assert note.decrypted_note == "Grace & peace — “amen”"

    def test_set_note_twice_keeps_only_the_latest_text(self):
        """Test that setting the note again replaces the old text."""
        note = _make_note()
        note.set_note("first")
        note.set_note("second")

        assert note.decrypted_note == "second"

    def test_decrypting_a_garbage_token_raises_invalid_token(self):
        """Test that a value that isn't a valid Fernet token can't be decrypted silently."""
        note = _make_note(encrypted_note="not-a-fernet-token")

        with self.assertRaises(InvalidToken):
            _ = note.decrypted_note

    def test_encrypted_note_is_not_editable(self):
        """Test that encrypted_note is marked non-editable, so forms and admin can't write it directly."""
        field = Note._meta.get_field("encrypted_note")

        assert field.editable is False


class TestNoteFieldDefinitions(SimpleTestCase):
    """The database columns for each Note field, as Django defines them."""

    def test_highlight_coordinates_defaults_to_empty_dict(self):
        """Test that a note with no highlight has empty coordinates by default."""
        field = Note._meta.get_field("highlight_coordinates")

        assert field.default() == {}
        assert field.blank is True

    def test_highlight_color_is_optional(self):
        """Test that a note with no highlight can store NULL for the color."""
        field = Note._meta.get_field("highlight_color")

        assert field.null is True
        assert field.blank is True
        assert field.max_length == 7

    def test_highlight_color_rejects_bad_values_in_validators(self):
        """Test that the color field's validator accepts #RRGGBB and rejects everything else."""
        validator = Note._meta.get_field("highlight_color").validators[0]

        validator("#FFFF00")
        for bad in ["FFFF00", "#FFF", "red", "#GGGGGG"]:
            with self.subTest(value=bad), self.assertRaises(ValidationError):
                validator(bad)

    def test_selected_html_is_a_text_field(self):
        """Test that the selected HTML is stored as text."""
        field = Note._meta.get_field("selected_html")

        assert isinstance(field, models.TextField)

    def test_verses_numbers_is_a_json_field(self):
        """Test that verse numbers are stored as JSON, which works on both Postgres and the SQLite test database."""
        field = Note._meta.get_field("verses_numbers")

        assert isinstance(field, models.JSONField)

    def test_user_foreign_key_cascades_on_delete(self):
        """Test that deleting a user also deletes their notes."""
        field = Note._meta.get_field("user")

        assert isinstance(field, models.ForeignKey)
        assert field.remote_field.on_delete is models.CASCADE

    def test_note_id_is_a_non_editable_uuid(self):
        """Test that the primary key is a UUID generated automatically."""
        field = Note._meta.get_field("id")

        assert field.primary_key is True
        assert field.editable is False
        assert callable(field.default)


class TestVerseNumbersCheck(SimpleTestCase):
    """parse_verses_numbers checks that verses_numbers is a JSON list of ints, and save() enforces it."""

    def test_a_json_string_is_parsed_into_a_list(self):
        """Test that JSON text such as "[16, 17]" is parsed into a list of ints."""
        assert parse_verses_numbers("[16, 17]") == [16, 17]

    def test_a_list_of_ints_is_accepted(self):
        """Test that a list of ints is returned unchanged."""
        assert parse_verses_numbers([16]) == [16]

    def test_an_empty_list_is_accepted(self):
        """Test that an empty list is accepted, since a note always has a list even if it has no verses."""
        assert parse_verses_numbers([]) == []

    def test_invalid_json_is_rejected(self):
        """Test that a string that isn't valid JSON raises ValueError."""
        with self.assertRaisesMessage(ValueError, "valid JSON"):
            parse_verses_numbers("[16, 17")

    def test_json_that_is_not_a_list_is_rejected(self):
        """Test that JSON that parses to a number, string, or object is rejected."""
        for bad in ["16", '"16"', '{"16": 1}', 16, {"16": 1}]:
            with self.subTest(value=bad), self.assertRaisesMessage(ValueError, "must be a list"):
                parse_verses_numbers(bad)

    def test_a_list_with_non_int_values_is_rejected(self):
        """Test that a list containing strings, floats, nested lists, or None is rejected."""
        for bad in [["16"], [16.0], [[16]], [None], [16, "17"]]:
            with self.subTest(value=bad), self.assertRaisesMessage(ValueError, "only ints"):
                parse_verses_numbers(bad)

    def test_bools_are_rejected_even_though_they_are_ints_in_python(self):
        """Test that True and False are rejected, since bool is a subclass of int."""
        for bad in [[True], [False], [16, True]]:
            with self.subTest(value=bad), self.assertRaisesMessage(ValueError, "only ints"):
                parse_verses_numbers(bad)

    def test_save_rejects_a_bad_value_before_writing(self):
        """Test that save() raises for a bad verses_numbers value before any database write happens."""
        note = _make_note(verses_numbers=["16"])

        with self.assertRaisesMessage(ValueError, "only ints"):
            note.save()

    def test_save_rejects_a_json_string_that_is_not_a_list(self):
        """Test that save() raises for JSON text that isn't a list."""
        note = _make_note(verses_numbers="16")

        with self.assertRaisesMessage(ValueError, "must be a list"):
            note.save()


class TestNoteDatabase(TestCase):
    """Saves notes to the SQLite test database and reads them back."""

    def setUp(self):
        self.user = User.objects.create_user(username="note-db-user", password="unused-test-password-123")

    def _save_note(self, **overrides):
        note = _make_note(user=self.user, **overrides)
        note.set_note("A saved thought")
        note.save()
        return note

    def test_verse_numbers_round_trip_as_a_list_of_ints(self):
        """Test that verse numbers come back from the database as the same list of ints."""
        note = self._save_note(verses_numbers=[16, 17])

        note.refresh_from_db()

        assert note.verses_numbers == [16, 17]

    def test_json_text_verse_numbers_are_saved_as_a_list(self):
        """Test that verses_numbers given as JSON text is parsed and saved as a list of ints."""
        note = self._save_note(verses_numbers="[16, 17]")

        note.refresh_from_db()

        assert note.verses_numbers == [16, 17]

    def test_highlight_fields_round_trip(self):
        """Test that the highlight coordinates and color are saved and loaded unchanged."""
        coordinates = {"16": {"beginning": 4, "end": 12}}
        note = self._save_note(highlight_coordinates=coordinates, highlight_color="#FFFF00")

        note.refresh_from_db()

        assert note.highlight_coordinates == coordinates
        assert note.highlight_color == "#FFFF00"

    def test_encrypted_note_is_decrypted_after_reload(self):
        """Test that the note text can be read back from the database."""
        note = self._save_note()

        reloaded = Note.objects.get(pk=note.pk)

        assert reloaded.decrypted_note == "A saved thought"

    def test_missing_highlight_is_saved_as_no_highlight(self):
        """Test that a note without a highlight loads with empty coordinates and no color."""
        note = self._save_note()

        note.refresh_from_db()

        assert note.highlight_coordinates == {}
        assert note.highlight_color is None

    def test_deleting_the_user_deletes_their_notes(self):
        """Test that the cascade removes the user's notes from the database."""
        note = self._save_note()

        self.user.delete()

        assert not Note.objects.filter(pk=note.pk).exists()
