import json
import uuid

from django.core.validators import RegexValidator
from django.db import models

from backend.models.user import User
from backend.utils.encryption import decrypt_note, encrypt_note


def parse_verses_numbers(value):
    """
    Check that verses_numbers is a list of ints, parsing it from JSON text first if needed.

    Parameters:
        value (list | str): The verse numbers, as a list or as a JSON string such as "[16, 17]".

    Returns:
        list[int]: The verse numbers as a list.

    Raises:
        ValueError: If the value isn't valid JSON, isn't a list, or contains anything other than ints.
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError("verses_numbers must be valid JSON.") from error
    if not isinstance(value, list):
        raise ValueError("verses_numbers must be a list.")
    # bool is a subclass of int, so True and False are rejected explicitly
    if not all(isinstance(number, int) and not isinstance(number, bool) for number in value):
        raise ValueError("verses_numbers must contain only ints.")
    return value


class Note(models.Model):
    """
    A note the user wrote about a selection of verses.

    The note text is encrypted with Fernet (see backend/utils/encryption.py) before it is stored in encrypted_note.
    Use set_note() to write it and decrypted_note to read it back. Don't assign to encrypted_note directly.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    collection_name = models.CharField(max_length=4)
    book = models.CharField(max_length=32)
    chapter = models.IntegerField()
    verses_text = models.TextField()
    selected_html = models.TextField()
    # Verse numbers in the note, e.g. [16, 17]. Stored as JSONField rather than ArrayField so the SQLite test database can save notes.
    verses_numbers = models.JSONField()
    # Maps verse number (as a string key) to {"beginning": int, "end": int}, the character offsets of the highlight in that verse.
    highlight_coordinates = models.JSONField(default=dict, blank=True)
    # Highlight color as a hex value, e.g. "#FFFF00".
    highlight_color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Enter a hex color like #FFFF00.")],
    )
    encrypted_note = models.TextField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        Save the note, after checking that verses_numbers is a list of ints (see parse_verses_numbers).

        A JSON string such as "[16, 17]" is parsed into a list before it is saved. Anything else raises an error and
        nothing is written.

        Raises:
            ValueError: If verses_numbers isn't valid JSON, isn't a list, or contains non-int values.
        """
        self.verses_numbers = parse_verses_numbers(self.verses_numbers)
        super().save(*args, **kwargs)

    def set_note(self, note_text):
        """
        Set the note text. Stores it encrypted in encrypted_note.

        Parameters:
            note_text (str): The note as the user wrote it.
        """
        self.encrypted_note = encrypt_note(note_text)

    @property
    def decrypted_note(self):
        """
        The note text, decrypted from encrypted_note. Use this to show the note to the user.

        Returns:
            str: The note as the user wrote it.

        Raises:
            cryptography.fernet.InvalidToken: If encrypted_note wasn't made with NOTE_ENCRYPTION_KEY.
        """
        return decrypt_note(self.encrypted_note)
