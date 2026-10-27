import hashlib

from django.contrib.auth.hashers import PBKDF2PasswordHasher


class PBKDF2SHA512PasswordHasher(PBKDF2PasswordHasher):
    """
    Django's default PBKDF2 hasher, using SHA-512 instead of SHA-256.

    Everything else is inherited from PBKDF2PasswordHasher: the iteration count, the salt, and the encoding.
    The algorithm name differs so stored hashes are never confused with the SHA-256 ones. Django requires a new
    name when the digest changes.
    """

    algorithm = "pbkdf2_sha512"
    digest = hashlib.sha512
