"""Tests for the note endpoints in backend.views.actions.note."""

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from backend.models.note import Note

User = get_user_model()
PASSWORD = "a-long-test-password-123"
YELLOW = "#FFFF00"
GREEN = "#00FF00"


def _make_note(user, **overrides):
    """Save a note for the user with a default verse, and return it."""
    fields = {
        "collection_name": "bsb",
        "book": "Genesis",
        "chapter": 1,
        "verses_text": "16) For God so loved the world",
        "selected_html": "For God so loved the world",
        "verses_numbers": [16],
    }
    fields.update(overrides)
    note = Note(user=user, **fields)
    note.set_note("The original note")
    note.save()
    return note


def _post_data(**overrides):
    """Form data for a note with a selection and a yellow highlight in verse 16."""
    data = {
        "collection_name": "bsb",
        "book": "Genesis",
        "chapter": "1",
        "note": "A new note",
        "verses_text": "16) For God so loved the world",
        "selected_html": "For God",
        "highlight_coordinates": json.dumps({"16": {"beginning": 0, "end": 7}}),
        "highlight_color": YELLOW,
    }
    data.update(overrides)
    return data


class TestPostNote(TestCase):
    """Tests for POST /accounts/post_note."""

    def setUp(self):
        self.url = reverse("api:post_note")
        self.user = User.objects.create_user(username="note-post-user", password=PASSWORD)
        self.client.force_login(self.user)

    def test_saves_the_note_and_asks_the_page_to_reload(self):
        """A valid post saves the note and returns HX-Refresh so htmx reloads the page."""
        response = self.client.post(self.url, _post_data())

        assert response.status_code == 200
        assert response["HX-Refresh"] == "true"
        note = Note.objects.get(user=self.user)
        assert note.collection_name == "bsb"
        assert note.book == "Genesis"
        assert note.chapter == 1
        assert note.decrypted_note == "A new note"

    def test_note_text_is_stored_encrypted(self):
        """The note text is never stored as typed."""
        self.client.post(self.url, _post_data(note="a private thought"))

        note = Note.objects.get(user=self.user)
        assert "a private thought" not in note.encrypted_note

    def test_verses_numbers_are_read_from_the_verse_lines(self):
        """Each line that starts with a verse number adds that number to verses_numbers."""
        self.client.post(self.url, _post_data(verses_text="16) For God\n17) For he gave"))

        assert Note.objects.get(user=self.user).verses_numbers == [16, 17]

    def test_general_note_with_no_verses_saves_an_empty_list(self):
        """A general note has no verse lines, so verses_numbers is an empty list and nothing is highlighted."""
        response = self.client.post(
            self.url,
            {"collection_name": "bsb", "book": "Genesis", "chapter": "1", "note": "About the chapter"},
        )

        assert response.status_code == 200
        note = Note.objects.get(user=self.user)
        assert note.verses_numbers == []
        assert note.selected_html == ""
        assert note.highlight_coordinates == {}
        assert note.highlight_color is None

    def test_selected_html_is_sanitized_and_keeps_red_words(self):
        """Scripts are removed from the saved HTML, and the red wj spans are kept."""
        self.client.post(
            self.url,
            _post_data(selected_html='<script>alert(1)</script><span class="wj">Jesus</span> said'),
        )

        selected_html = Note.objects.get(user=self.user).selected_html
        assert "<script" not in selected_html
        assert '<span class="wj">Jesus</span>' in selected_html

    def test_highlight_is_saved(self):
        """The highlight coordinates and color are saved with the note."""
        self.client.post(self.url, _post_data())

        note = Note.objects.get(user=self.user)
        assert note.highlight_coordinates == {"16": {"beginning": 0, "end": 7}}
        assert note.highlight_color == YELLOW

    def test_coordinates_without_a_color_are_rejected(self):
        """A highlight needs both coordinates and a color, so a partial highlight saves nothing."""
        response = self.client.post(self.url, _post_data(highlight_color=""))

        assert response.status_code == 422
        assert not Note.objects.filter(user=self.user).exists()

    def test_invalid_highlight_coordinates_are_rejected(self):
        """Coordinates with a bad verse key are rejected and nothing is saved."""
        bad = json.dumps({"0": {"beginning": 0, "end": 7}})

        response = self.client.post(self.url, _post_data(highlight_coordinates=bad))

        assert response.status_code == 422
        assert not Note.objects.filter(user=self.user).exists()

    def test_post_without_a_csrf_token_is_refused(self):
        """A post without a valid CSRF token gets a 403 and saves nothing."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)

        response = client.post(self.url, _post_data())

        assert response.status_code == 403
        assert not Note.objects.filter(user=self.user).exists()


class TestPostNoteSignedOut(TestCase):
    """A signed-out visitor must not be able to save a note."""

    def test_anonymous_post_is_refused_and_saves_nothing(self):
        """A signed-out post gets a 401 and no note is written."""
        response = Client().post(reverse("api:post_note"), _post_data())

        assert response.status_code == 401
        assert Note.objects.count() == 0


class TestUpdateNote(TestCase):
    """Tests for POST /accounts/update_note."""

    def setUp(self):
        self.url = reverse("api:update_note")
        self.user = User.objects.create_user(username="note-update-user", password=PASSWORD)
        self.client.force_login(self.user)
        self.note = _make_note(
            self.user, highlight_coordinates={"16": {"beginning": 0, "end": 7}}, highlight_color=YELLOW
        )

    def test_updates_the_text_and_color_of_the_users_note(self):
        """The owner can change the note text and the highlight color."""
        response = self.client.post(
            self.url, {"note_id": str(self.note.id), "note": "Changed", "highlight_color": GREEN}
        )

        assert response.status_code == 200
        assert response["HX-Refresh"] == "true"
        self.note.refresh_from_db()
        assert self.note.decrypted_note == "Changed"
        assert self.note.highlight_color == GREEN

    def test_blank_color_removes_the_highlight_color(self):
        """Leaving the color blank clears it, so the note is no longer highlighted."""
        self.client.post(self.url, {"note_id": str(self.note.id), "note": "Changed", "highlight_color": ""})

        self.note.refresh_from_db()
        assert self.note.highlight_color is None

    def test_update_does_not_change_the_highlight_coordinates(self):
        """Updates only change the text and color, never the coordinates."""
        self.client.post(self.url, {"note_id": str(self.note.id), "note": "Changed", "highlight_color": GREEN})

        self.note.refresh_from_db()
        assert self.note.highlight_coordinates == {"16": {"beginning": 0, "end": 7}}

    def test_another_users_note_is_not_found(self):
        """A user can't change someone else's note, and gets a 404 with the note unchanged."""
        other = User.objects.create_user(username="note-other-user", password=PASSWORD)
        other_note = _make_note(other)

        response = self.client.post(self.url, {"note_id": str(other_note.id), "note": "Hacked", "highlight_color": ""})

        assert response.status_code == 404
        other_note.refresh_from_db()
        assert other_note.decrypted_note == "The original note"

    def test_anonymous_user_is_refused(self):
        """A signed-out visitor gets a 401 and the note is unchanged."""
        self.client.logout()

        response = self.client.post(self.url, {"note_id": str(self.note.id), "note": "Changed", "highlight_color": ""})

        assert response.status_code == 401
        self.note.refresh_from_db()
        assert self.note.decrypted_note == "The original note"

    def test_invalid_note_id_is_rejected(self):
        """A note_id that isn't a UUID is rejected before anything is looked up."""
        response = self.client.post(self.url, {"note_id": "not-a-uuid", "note": "Changed", "highlight_color": ""})

        assert response.status_code == 422


class TestDeleteNote(TestCase):
    """Tests for POST /accounts/delete_note."""

    def setUp(self):
        self.url = reverse("api:delete_note")
        self.user = User.objects.create_user(username="note-delete-user", password=PASSWORD)
        self.client.force_login(self.user)
        self.note = _make_note(self.user)

    def test_deletes_the_users_note(self):
        """The owner can delete their note, and the page is asked to reload."""
        response = self.client.post(self.url, {"note_id": str(self.note.id)})

        assert response.status_code == 200
        assert response["HX-Refresh"] == "true"
        assert not Note.objects.filter(pk=self.note.pk).exists()

    def test_another_users_note_is_not_found_and_kept(self):
        """A user can't delete someone else's note, and gets a 404 with the note kept."""
        other = User.objects.create_user(username="note-delete-other", password=PASSWORD)
        other_note = _make_note(other)

        response = self.client.post(self.url, {"note_id": str(other_note.id)})

        assert response.status_code == 404
        assert Note.objects.filter(pk=other_note.pk).exists()

    def test_anonymous_user_is_refused(self):
        """A signed-out visitor gets a 401 and the note is kept."""
        self.client.logout()

        response = self.client.post(self.url, {"note_id": str(self.note.id)})

        assert response.status_code == 401
        assert Note.objects.filter(pk=self.note.pk).exists()
