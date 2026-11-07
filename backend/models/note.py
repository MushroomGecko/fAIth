import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models

from backend.models.user import User
from backend.utils.encryption import decrypt_note, encrypt_note


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
    selected_text = models.TextField()
    verses_numbers = ArrayField(models.IntegerField())
    encrypted_note = models.TextField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
