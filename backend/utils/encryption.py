import json

from cryptography.fernet import Fernet
from django.conf import settings

# Private helpers shared by every kind of encrypted value below. Each takes the name of the settings key to use,
# so a new kind of value only needs its key added to settings.py and a few one-line wrappers.


def _cipher(key_setting):
    """
    Return a Fernet cipher built from the key named in settings.

    Parameters:
        key_setting (str): The name of the Fernet key setting, e.g. "NOTE_ENCRYPTION_KEY".

    Returns:
        Fernet: The cipher for that key.
    """
    return Fernet(getattr(settings, key_setting))


def _encrypt_text(key_setting, text):
    """
    Encrypt a string with the key named in settings.

    Parameters:
        key_setting (str): The name of the Fernet key setting.
        text (str): The plain text to encrypt.

    Returns:
        str: The Fernet token, as text.
    """
    return _cipher(key_setting).encrypt(text.encode()).decode("ascii")


def _decrypt_text(key_setting, token):
    """
    Decrypt a Fernet token with the key named in settings.

    Parameters:
        key_setting (str): The name of the Fernet key setting.
        token (str): The Fernet token, as text.

    Returns:
        str: The plain text that was encrypted.

    Raises:
        cryptography.fernet.InvalidToken: If the token wasn't made with that key.
    """
    return _cipher(key_setting).decrypt(token.encode("ascii")).decode()


# Recovery codes


def recovery_session_cipher():
    """
    Return the Fernet cipher for the recovery codes kept in the session during signup and recovery.

    Returns:
        Fernet: The cipher built from RECOVERY_CODE_ENCRYPTION_KEY.
    """
    return _cipher("RECOVERY_CODE_ENCRYPTION_KEY")


async def encrypt_recovery_codes(codes):
    """
    Encrypt the recovery codes kept in the session during signup and recovery.

    Parameters:
        codes (list[str]): The plain-text recovery codes.

    Returns:
        str: The Fernet token, as text.
    """
    return _encrypt_text("RECOVERY_CODE_ENCRYPTION_KEY", json.dumps(codes))


async def decrypt_recovery_codes(token):
    """
    Decrypt the recovery codes kept in the session.

    Parameters:
        token (str): The Fernet token from the session.

    Returns:
        list[str]: The recovery codes.

    Raises:
        cryptography.fernet.InvalidToken: If the token wasn't made with RECOVERY_CODE_ENCRYPTION_KEY.
    """
    return json.loads(_decrypt_text("RECOVERY_CODE_ENCRYPTION_KEY", token))


# TOTP (authenticator app) secrets


def totp_key_cipher():
    """
    Return the Fernet cipher for TOTP secrets. It has its own key, so it can be rotated apart from the recovery codes.

    Returns:
        Fernet: The cipher built from TOTP_ENCRYPTION_KEY.
    """
    return _cipher("TOTP_ENCRYPTION_KEY")


def encrypt_totp_key(hex_key):
    """
    Encrypt a hex-encoded TOTP secret for storage.

    Parameters:
        hex_key (str): The plain hex secret.

    Returns:
        str: The Fernet token, as text.
    """
    return _encrypt_text("TOTP_ENCRYPTION_KEY", hex_key)


def decrypt_totp_key(token):
    """
    Decrypt a stored TOTP secret.

    Parameters:
        token (str): The Fernet token from the database.

    Returns:
        str: The plain hex secret.

    Raises:
        cryptography.fernet.InvalidToken: If the token wasn't made with TOTP_ENCRYPTION_KEY.
    """
    return _decrypt_text("TOTP_ENCRYPTION_KEY", token)


# Usernames


def username_cipher():
    """
    Return the Fernet cipher for the usernames shown to the user. It has its own key, so it can be rotated apart
    from the other keys.

    Returns:
        Fernet: The cipher built from USERNAME_ENCRYPTION_KEY.
    """
    return _cipher("USERNAME_ENCRYPTION_KEY")


def encrypt_username(username):
    """
    Encrypt a username for storage in encrypted_username.

    Parameters:
        username (str): The username, already NFKC-normalized by User.set_username().

    Returns:
        str: The Fernet token, as text.
    """
    return _encrypt_text("USERNAME_ENCRYPTION_KEY", username)


def decrypt_username(token):
    """
    Decrypt a username stored in encrypted_username.

    Parameters:
        token (str): The Fernet token from the database.

    Returns:
        str: The username as it was stored, which is the NFKC-normalized name.

    Raises:
        cryptography.fernet.InvalidToken: If the token wasn't made with USERNAME_ENCRYPTION_KEY.
    """
    return _decrypt_text("USERNAME_ENCRYPTION_KEY", token)


# Notes


def note_cipher():
    """
    Return the Fernet cipher for the text of each note. It has its own key, so it can be rotated apart from the others.

    Returns:
        Fernet: The cipher built from NOTE_ENCRYPTION_KEY.
    """
    return _cipher("NOTE_ENCRYPTION_KEY")


def encrypt_note(note_text):
    """
    Encrypt the text of a note for storage in Note.encrypted_note.

    Parameters:
        note_text (str): The note as the user wrote it.

    Returns:
        str: The Fernet token, as text.
    """
    return _encrypt_text("NOTE_ENCRYPTION_KEY", note_text)


def decrypt_note(token):
    """
    Decrypt the text of a note stored in Note.encrypted_note.

    Parameters:
        token (str): The Fernet token from the database.

    Returns:
        str: The note as the user wrote it.

    Raises:
        cryptography.fernet.InvalidToken: If the token wasn't made with NOTE_ENCRYPTION_KEY.
    """
    return _decrypt_text("NOTE_ENCRYPTION_KEY", token)
