import json

from cryptography.fernet import Fernet
from django.conf import settings

# Recovery codes


def recovery_session_cipher():
    """
    Return the Fernet cipher for the recovery codes kept in the session during signup and recovery.

    Returns:
        Fernet: The cipher built from RECOVERY_CODE_ENCRYPTION_KEY.
    """
    return Fernet(settings.RECOVERY_CODE_ENCRYPTION_KEY)


async def encrypt_recovery_codes(codes):
    """
    Encrypt the recovery codes kept in the session during signup and recovery.

    Parameters:
        codes (list[str]): The plain-text recovery codes.

    Returns:
        str: The Fernet token, as text.
    """
    return recovery_session_cipher().encrypt(json.dumps(codes).encode()).decode("ascii")


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
    return json.loads(recovery_session_cipher().decrypt(token.encode("ascii")))


# TOTP (authenticator app) secrets


def totp_key_cipher():
    """
    Return the Fernet cipher for TOTP secrets. It has its own key, so it can be rotated apart from the recovery codes.

    Returns:
        Fernet: The cipher built from TOTP_ENCRYPTION_KEY.
    """
    return Fernet(settings.TOTP_ENCRYPTION_KEY)


def encrypt_totp_key(hex_key):
    """
    Encrypt a hex-encoded TOTP secret for storage.

    Parameters:
        hex_key (str): The plain hex secret.

    Returns:
        str: The Fernet token, as text.
    """
    return totp_key_cipher().encrypt(hex_key.encode("ascii")).decode("ascii")


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
    return totp_key_cipher().decrypt(token.encode("ascii")).decode("ascii")


# Usernames


def username_cipher():
    """
    Return the Fernet cipher for the usernames shown to the user. It has its own key, so it can be rotated apart
    from the other keys.

    Returns:
        Fernet: The cipher built from USERNAME_ENCRYPTION_KEY.
    """
    return Fernet(settings.USERNAME_ENCRYPTION_KEY)


def encrypt_username(username):
    """
    Encrypt a username for storage in username_display.

    Parameters:
        username (str): The username, already NFKC-normalized by User.set_username().

    Returns:
        str: The Fernet token, as text.
    """
    return username_cipher().encrypt(username.encode()).decode("ascii")


def decrypt_username(token):
    """
    Decrypt a username stored in username_display.

    Parameters:
        token (str): The Fernet token from the database.

    Returns:
        str: The username as it was stored, which is the NFKC-normalized name.

    Raises:
        cryptography.fernet.InvalidToken: If the token wasn't made with USERNAME_ENCRYPTION_KEY.
    """
    return username_cipher().decrypt(token.encode("ascii")).decode()
