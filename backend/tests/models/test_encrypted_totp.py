"""Tests for the encrypted authenticator app device in backend.models.encrypted_totp."""

from binascii import unhexlify

from cryptography.fernet import Fernet, InvalidToken
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django_otp.oath import TOTP

from backend.models import EncryptedTOTPDevice
from backend.models.encrypted_totp import TOTP_SECRET_BYTES, default_encrypted_key
from backend.utils.encryption import decrypt_totp_key, encrypt_totp_key

HEX_SECRET = "3fa2c9d107b4e8a56c1d0f93b2e75a4823ab91fc"
# A Fernet key that differs from the test settings, to check that a device can't be read with the wrong key.
OTHER_KEY = Fernet.generate_key().decode()
PASSWORD = "a-long-test-password-123"


def _current_code(device):
    """Return the 6-digit code the authenticator app would show for this device right now."""
    return str(TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift).token()).zfill(device.digits)


class TestEncryptedTOTPDevice(TestCase):
    """Checks that the TOTP secret is encrypted at rest and decrypts only with the right key."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="totp-model-user", password=PASSWORD)

    def _device_with_secret(self, hex_secret=HEX_SECRET):
        """Create a saved device whose encrypted_key holds the given hex secret, encrypted with the current key."""
        return EncryptedTOTPDevice.objects.create(
            user=self.user, name="Authenticator app", confirmed=True, encrypted_key=encrypt_totp_key(hex_secret)
        )

    def test_secret_is_stored_encrypted_not_as_plain_hex(self):
        """The database holds a Fernet token, not the hex secret."""
        device = self._device_with_secret()
        device.refresh_from_db()

        assert device.encrypted_key != HEX_SECRET
        assert HEX_SECRET not in device.encrypted_key
        assert device.encrypted_key.startswith("gAAAA")

    def test_bin_key_decrypts_the_stored_secret(self):
        """bin_key is the original secret in binary form, recovered from encrypted_key."""
        device = self._device_with_secret()

        assert device.bin_key == unhexlify(HEX_SECRET)

    def test_bin_key_still_works_after_a_reload(self):
        """A device read back from the database decrypts to the same secret."""
        device = self._device_with_secret()
        reloaded = EncryptedTOTPDevice.objects.get(pk=device.pk)

        assert reloaded.bin_key == unhexlify(HEX_SECRET)

    def test_secret_cannot_be_read_with_a_different_key(self):
        """Changing TOTP_ENCRYPTION_KEY makes the stored secret unreadable, so the device can't be used."""
        device = self._device_with_secret()

        with override_settings(TOTP_ENCRYPTION_KEY=OTHER_KEY), self.assertRaises(InvalidToken):
            _ = device.bin_key

    def test_new_device_gets_a_random_secret_of_the_right_length(self):
        """A device created without a secret gets a new one, 20 bytes long, already encrypted."""
        device = EncryptedTOTPDevice(user=self.user, name="Authenticator app", confirmed=False)

        assert len(decrypt_totp_key(device.encrypted_key)) == TOTP_SECRET_BYTES * 2
        assert len(device.bin_key) == TOTP_SECRET_BYTES

    def test_each_new_device_gets_a_different_secret(self):
        """Two devices never share a secret."""
        first = EncryptedTOTPDevice(user=self.user, name="Authenticator app", confirmed=False)
        second = EncryptedTOTPDevice(user=self.user, name="Authenticator app", confirmed=False)

        assert first.bin_key != second.bin_key

    def test_default_key_function_returns_an_encrypted_secret(self):
        """The field default is an encrypted token that decrypts to a hex secret."""
        token = default_encrypted_key()

        assert token.startswith("gAAAA")
        assert len(decrypt_totp_key(token)) == TOTP_SECRET_BYTES * 2

    def test_code_from_the_stored_secret_verifies(self):
        """A code generated from the decrypted secret is accepted by the device, which uses the same secret."""
        device = self._device_with_secret()

        assert device.verify_token(_current_code(device))

    def test_wrong_code_is_rejected(self):
        """A code that doesn't match the secret is refused."""
        device = self._device_with_secret()
        correct = _current_code(device)
        wrong = "000000" if correct != "000000" else "111111"

        assert not device.verify_token(wrong)

    def test_device_is_unconfirmed_when_created_unconfirmed(self):
        """A device created unconfirmed stays unconfirmed until the user confirms it with a code."""
        device = EncryptedTOTPDevice.objects.create(user=self.user, name="Authenticator app", confirmed=False)
        device.refresh_from_db()

        assert not device.confirmed
