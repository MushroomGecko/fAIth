"""Tests for the encryption helpers in backend.utils.encryption."""

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.test import TestCase, override_settings

from backend.utils.encryption import (
    decrypt_recovery_codes,
    decrypt_totp_key,
    decrypt_username,
    encrypt_recovery_codes,
    encrypt_totp_key,
    encrypt_username,
    recovery_session_cipher,
    totp_key_cipher,
    username_cipher,
)

# A Fernet key that differs from the test settings, used to check that data encrypted with one key can't be read
# with another.
OTHER_KEY = Fernet.generate_key().decode()
HEX_SECRET = "3fa2c9d107b4e8a56c1d0f93b2e75a4823ab91fc"
# Recovery codes in the format new_recovery_code() produces: 32 lowercase hex characters in four dash-separated groups.
RECOVERY_CODES = ["3fa2c9d1-07b4e8a5-6c1d0f93-b2e75a48", "9e4b07c2-1a6d3f85-d0c4e72b-58f1a9e6"]


def _settings_key(name):
    """Return the Fernet key from the settings, as bytes, by setting name."""
    return getattr(settings, name).encode()


class TestCipherKeys(TestCase):
    """Tests for recovery_session_cipher and totp_key_cipher."""

    def test_recovery_cipher_uses_recovery_key(self):
        """The recovery cipher is built from RECOVERY_CODE_ENCRYPTION_KEY."""
        token = recovery_session_cipher().encrypt(b"codes")

        assert Fernet(_settings_key("RECOVERY_CODE_ENCRYPTION_KEY")).decrypt(token) == b"codes"

    def test_totp_cipher_uses_totp_key(self):
        """The TOTP cipher is built from TOTP_ENCRYPTION_KEY."""
        token = totp_key_cipher().encrypt(b"secret")

        assert Fernet(_settings_key("TOTP_ENCRYPTION_KEY")).decrypt(token) == b"secret"

    def test_recovery_token_cannot_be_read_with_totp_key(self):
        """A token from the recovery cipher is refused by the TOTP cipher, so the two keys can't be swapped."""
        token = recovery_session_cipher().encrypt(b"codes")

        with self.assertRaises(InvalidToken):
            totp_key_cipher().decrypt(token)

    def test_totp_token_cannot_be_read_with_recovery_key(self):
        """A token from the TOTP cipher is refused by the recovery cipher."""
        token = totp_key_cipher().encrypt(b"secret")

        with self.assertRaises(InvalidToken):
            recovery_session_cipher().decrypt(token)


class TestEncryptTotpKey(TestCase):
    """Tests for encrypt_totp_key and decrypt_totp_key."""

    def test_round_trip_returns_original_secret(self):
        """Decrypting an encrypted secret gives back the same hex string."""
        token = encrypt_totp_key(HEX_SECRET)

        assert decrypt_totp_key(token) == HEX_SECRET

    def test_encrypted_value_is_text_and_hides_secret(self):
        """The stored value is a str and doesn't contain the plain secret."""
        token = encrypt_totp_key(HEX_SECRET)

        assert isinstance(token, str)
        assert HEX_SECRET not in token

    def test_same_secret_gives_different_tokens(self):
        """Fernet adds a random nonce, so encrypting the same secret twice gives two different tokens."""
        assert encrypt_totp_key(HEX_SECRET) != encrypt_totp_key(HEX_SECRET)

    def test_wrong_key_is_refused(self):
        """A token made with one TOTP key raises InvalidToken under another key, so it can't be used silently."""
        token = encrypt_totp_key(HEX_SECRET)

        with override_settings(TOTP_ENCRYPTION_KEY=OTHER_KEY):
            with self.assertRaises(InvalidToken):
                decrypt_totp_key(token)

    def test_garbage_token_is_refused(self):
        """A value that isn't a Fernet token raises InvalidToken."""
        with self.assertRaises(InvalidToken):
            decrypt_totp_key("not-a-fernet-token")

    def test_tampered_token_is_refused(self):
        """Changing one character of a valid token makes decryption fail, so the secret can't be altered unnoticed."""
        token = encrypt_totp_key(HEX_SECRET)
        flipped = "A" if token[-1] != "A" else "B"
        tampered = token[:-1] + flipped

        with self.assertRaises(InvalidToken):
            decrypt_totp_key(tampered)


class TestUsernameCipher(TestCase):
    """Tests for username_cipher, encrypt_username, and decrypt_username."""

    def test_cipher_uses_username_key(self):
        """The username cipher is built from USERNAME_ENCRYPTION_KEY."""
        token = username_cipher().encrypt(b"Alice")

        assert Fernet(_settings_key("USERNAME_ENCRYPTION_KEY")).decrypt(token) == b"Alice"

    def test_round_trip_keeps_letter_case(self):
        """Decrypting gives back the username exactly as typed, including its letter case."""
        token = encrypt_username("MixedCase-Name")

        assert decrypt_username(token) == "MixedCase-Name"

    def test_encrypted_value_is_text_and_hides_name(self):
        """The stored value is a str and doesn't contain the plain username."""
        token = encrypt_username("plain-name")

        assert isinstance(token, str)
        assert "plain-name" not in token

    def test_same_name_gives_different_tokens(self):
        """Fernet adds a random nonce, so two tokens for the same name don't match each other."""
        assert encrypt_username("same-name") != encrypt_username("same-name")

    def test_wrong_key_is_refused(self):
        """A token made with one username key raises InvalidToken under another."""
        token = encrypt_username("plain-name")

        with override_settings(USERNAME_ENCRYPTION_KEY=OTHER_KEY):
            with self.assertRaises(InvalidToken):
                decrypt_username(token)

    def test_totp_key_token_is_refused(self):
        """A token made with the TOTP key is refused, so the two kinds of value can't be swapped."""
        token = encrypt_totp_key(HEX_SECRET)

        with self.assertRaises(InvalidToken):
            decrypt_username(token)

    def test_garbage_token_is_refused(self):
        """A value that isn't a Fernet token raises InvalidToken."""
        with self.assertRaises(InvalidToken):
            decrypt_username("not-a-fernet-token")


class TestEncryptRecoveryCodes(TestCase):
    """Tests for encrypt_recovery_codes and decrypt_recovery_codes."""

    async def test_round_trip_returns_original_codes(self):
        """Decrypting the encrypted codes gives back the same list, in the same order."""
        token = await encrypt_recovery_codes(RECOVERY_CODES)

        assert await decrypt_recovery_codes(token) == RECOVERY_CODES

    async def test_encrypted_value_is_text_and_hides_codes(self):
        """The stored value is a str and doesn't contain any plain recovery code."""
        token = await encrypt_recovery_codes(RECOVERY_CODES)

        assert isinstance(token, str)
        for code in RECOVERY_CODES:
            assert code not in token

    async def test_wrong_key_is_refused(self):
        """Codes encrypted with one recovery key raise InvalidToken under another, so they can't be read silently."""
        token = await encrypt_recovery_codes(RECOVERY_CODES)

        with override_settings(RECOVERY_CODE_ENCRYPTION_KEY=OTHER_KEY):
            with self.assertRaises(InvalidToken):
                await decrypt_recovery_codes(token)

    async def test_garbage_token_is_refused(self):
        """A value that isn't a Fernet token raises InvalidToken."""
        with self.assertRaises(InvalidToken):
            await decrypt_recovery_codes("not-a-fernet-token")

    async def test_totp_key_token_is_refused(self):
        """A token made with the TOTP key is refused, so the two kinds of secret can't be swapped."""
        token = encrypt_totp_key(HEX_SECRET)

        with self.assertRaises(InvalidToken):
            await decrypt_recovery_codes(token)
