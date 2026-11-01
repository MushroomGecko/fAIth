"""Tests for the SHA-512 password hasher in backend.utils.hashing, and that it's the only hasher Django accepts."""

import base64
import hashlib
import hmac

from django.conf import settings
from django.contrib.auth.hashers import (
    MD5PasswordHasher,
    PBKDF2PasswordHasher,
    PBKDF2SHA1PasswordHasher,
    ScryptPasswordHasher,
    check_password,
    get_hasher,
    identify_hasher,
    make_password,
)
from django.test import SimpleTestCase, override_settings

from backend.utils.hashing import PBKDF2SHA512PasswordHasher, username_hmac

PASSWORD = "a-long-test-password-123"
SALT = "testsalt"
# A low iteration count keeps these tests fast. The hasher's real default is used only where a test needs it.
FAST_ITERATIONS = 1000
HASHER_PATH = "backend.utils.hashing.PBKDF2SHA512PasswordHasher"


class TestDjangoUsesOnlyOurHasher(SimpleTestCase):
    """Checks that SHA-512 is the only hasher Django accepts, and that new passwords are stored with it."""

    def test_sha512_is_the_only_hasher_in_settings(self):
        """PASSWORD_HASHERS lists just the SHA-512 hasher, so no other algorithm can be used."""
        assert settings.PASSWORD_HASHERS == [HASHER_PATH]

    def test_default_hasher_is_ours(self):
        """The default hasher Django returns is the SHA-512 hasher."""
        assert isinstance(get_hasher(), PBKDF2SHA512PasswordHasher)

    def test_new_password_is_stored_with_sha512(self):
        """A password hashed with make_password uses the pbkdf2_sha512 algorithm."""
        encoded = make_password(PASSWORD)

        assert encoded.startswith("pbkdf2_sha512$")
        assert identify_hasher(encoded).algorithm == "pbkdf2_sha512"

    def test_new_password_uses_django_default_iterations(self):
        """
        The SHA-512 hasher keeps Django's default iteration count, so only the digest differs.

        Django's default for PBKDF2PasswordHasher is 1,200,000 iterations in Django 6.0.6. Django raises this
        default between releases, so the test compares against the class attribute and not a fixed number.
        """
        assert get_hasher().iterations == PBKDF2PasswordHasher.iterations

    def test_other_algorithms_are_rejected(self):
        """Hashes from every other algorithm Django ships raise ValueError, because none of them is in PASSWORD_HASHERS."""
        # Hashes from algorithms that need no extra packages are produced by their own hasher classes.
        # Argon2 and bcrypt need third-party packages, so their hashes are written out. Django rejects an
        # algorithm by its name before it hashes anything, so the exact contents of those strings don't matter.
        other_hashes = {
            "pbkdf2_sha256": PBKDF2PasswordHasher().encode(PASSWORD, SALT, FAST_ITERATIONS),
            "pbkdf2_sha1": PBKDF2SHA1PasswordHasher().encode(PASSWORD, SALT, FAST_ITERATIONS),
            "md5": MD5PasswordHasher().encode(PASSWORD, SALT),
            "scrypt": ScryptPasswordHasher().encode(PASSWORD, SALT),
            "argon2": "argon2$argon2id$v=19$m=102400,t=2,p=8$c2FsdHNhbHQ$aGFzaGhhc2hoYXNo",
            "bcrypt_sha256": "bcrypt_sha256$$2b$12$abcdefghijklmnopqrstuuABCDEFGHIJKLMNOPQRSTUVWXYZ012345",
        }

        for algorithm, encoded in other_hashes.items():
            with self.subTest(algorithm=algorithm):
                # Django looks the algorithm up before verifying, and treats an unknown one as a failed check.
                with self.assertRaises(ValueError):
                    identify_hasher(encoded)
                assert check_password(PASSWORD, encoded) is False


class TestSha512Hasher(SimpleTestCase):
    """Checks that the SHA-512 hasher itself encodes, verifies, and rejects passwords correctly."""

    def setUp(self):
        self.hasher = PBKDF2SHA512PasswordHasher()

    def test_correct_password_verifies(self):
        """The right password passes check_password."""
        encoded = self.hasher.encode(PASSWORD, SALT, FAST_ITERATIONS)

        assert check_password(PASSWORD, encoded)

    def test_wrong_password_is_rejected(self):
        """A different password fails check_password."""
        encoded = self.hasher.encode(PASSWORD, SALT, FAST_ITERATIONS)

        assert not check_password("wrong-password-123", encoded)

    def test_digest_is_pbkdf2_hmac_sha512(self):
        """The stored hash is PBKDF2-HMAC-SHA512 of the password, computed with the stored salt and iterations."""
        encoded = self.hasher.encode(PASSWORD, SALT, FAST_ITERATIONS)
        stored_hash = encoded.split("$", 3)[3]
        expected = hashlib.pbkdf2_hmac("sha512", PASSWORD.encode(), SALT.encode(), FAST_ITERATIONS)

        assert base64.b64decode(stored_hash) == expected

    def test_same_password_with_different_salts_gives_different_hashes(self):
        """Each password gets its own salt, so equal passwords don't share a stored hash."""
        first = self.hasher.encode(PASSWORD, "saltone", FAST_ITERATIONS)
        second = self.hasher.encode(PASSWORD, "salttwo", FAST_ITERATIONS)

        assert first != second

    def test_decode_returns_stored_parts(self):
        """decode returns the algorithm, salt, and iteration count that were stored."""
        encoded = self.hasher.encode(PASSWORD, SALT, FAST_ITERATIONS)
        decoded = self.hasher.decode(encoded)

        assert decoded["algorithm"] == "pbkdf2_sha512"
        assert decoded["salt"] == SALT
        assert decoded["iterations"] == FAST_ITERATIONS


class TestUsernameHmac(SimpleTestCase):
    """Tests for username_hmac, the keyed HMAC-SHA512 stored in User.username."""

    def test_digest_is_hmac_sha512_of_lowercase_name(self):
        """The value is the HMAC-SHA512 of the lowercase username, keyed with USERNAME_HMAC_KEY, as hex."""
        expected = hmac.new(settings.USERNAME_HMAC_KEY.encode(), b"alice", hashlib.sha512).hexdigest()

        assert username_hmac("Alice") == expected

    def test_is_128_hex_characters(self):
        """SHA-512 gives 64 bytes, which is 128 hex characters, so it fits the username column."""
        value = username_hmac("alice")

        assert len(value) == 128
        assert all(character in "0123456789abcdef" for character in value)

    def test_ignores_letter_case(self):
        """Names that differ only in letter case give the same value, matching signup's rule."""
        assert username_hmac("MixedCase") == username_hmac("mixedcase") == username_hmac("MIXEDCASE")

    def test_different_names_give_different_values(self):
        """Different usernames don't share a stored value."""
        assert username_hmac("alice") != username_hmac("bob")

    def test_nfkc_equivalent_names_match(self):
        """Full-width letters normalize to ASCII first, so they give the same value as the ASCII name."""
        assert username_hmac("\uff41lice") == username_hmac("alice")

    def test_value_is_not_the_plain_name(self):
        """The stored value doesn't contain the username."""
        assert "alice" not in username_hmac("alice")

    def test_different_key_gives_different_value(self):
        """Changing USERNAME_HMAC_KEY changes every value, so the key has to be kept secret and stable."""
        original = username_hmac("alice")

        with override_settings(USERNAME_HMAC_KEY="another-key"):
            assert username_hmac("alice") != original
