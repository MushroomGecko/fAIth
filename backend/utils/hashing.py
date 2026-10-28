import hashlib
import hmac
import unicodedata

from django.conf import settings
from django.contrib.auth.hashers import PBKDF2PasswordHasher


def username_hmac(username):
    """
    Return the keyed HMAC-SHA512 of a username, used as its lookup value in the database.

    The username is NFKC-normalized and lowercased first, so names that differ only in letter case give the same
    value. That matches signup's rule that usernames can't differ only in case. The HMAC key is USERNAME_HMAC_KEY,
    so the stored value can't be reversed or checked against a list of names without that key.

    Parameters:
        username (str): The username as the user typed it.

    Returns:
        str: The HMAC as 128 lowercase hex characters.
    """
    normalized = unicodedata.normalize("NFKC", username).lower()
    return hmac.new(settings.USERNAME_HMAC_KEY.encode(), normalized.encode(), hashlib.sha512).hexdigest()


class PBKDF2SHA512PasswordHasher(PBKDF2PasswordHasher):
    """
    Django's default PBKDF2 hasher, using SHA-512 instead of SHA-256.

    Everything else is inherited from PBKDF2PasswordHasher: the iteration count, the salt, and the encoding.
    The algorithm name differs so stored hashes are never confused with the SHA-256 ones. Django requires a new
    name when the digest changes.
    """

    algorithm = "pbkdf2_sha512"
    digest = hashlib.sha512
