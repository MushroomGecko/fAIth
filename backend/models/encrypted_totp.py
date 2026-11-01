from binascii import unhexlify

from django.db import models
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.util import random_hex

from backend.utils.encryption import decrypt_totp_key, encrypt_totp_key

# Size of a new TOTP secret, in bytes. 20 bytes is 160 bits, which is the length of the SHA-1 output that
# TOTP uses (django_otp's config_url sets the algorithm to SHA1). RFC 6238 says keys SHOULD be the length of the
# HMAC output, so 20 bytes matches it. RFC 4226 requires at least 128 bits (16 bytes) and recommends 160 bits.
# This is also the size django_otp uses for its own default key. See:
#   https://www.rfc-editor.org/rfc/rfc6238 (section 5.1, key length)
#   https://www.rfc-editor.org/rfc/rfc4226 (section 4, shared secret length)
TOTP_SECRET_BYTES = 20


def default_encrypted_key():
    """
    Return a new random TOTP secret, already encrypted. Used as the field default.

    Returns:
        str: The encrypted secret, ready to store.
    """
    return encrypt_totp_key(random_hex(TOTP_SECRET_BYTES))


class EncryptedTOTPDevice(TOTPDevice):
    """
    An authenticator app (TOTP) device whose secret is encrypted at rest.

    The real secret lives only in encrypted_key, as a Fernet token made with TOTP_ENCRYPTION_KEY. The inherited
    key column is never set by this code. It keeps the random value django_otp gives every new device, which
    isn't the real secret. bin_key decrypts encrypted_key, so django_otp's verify_token and config_url use the
    real secret.
    """

    encrypted_key = models.TextField(
        default=default_encrypted_key,
        help_text="The hex-encoded TOTP secret, encrypted with TOTP_ENCRYPTION_KEY.",
    )

    @property
    def bin_key(self):
        """
        The real secret as a binary string, decrypted from encrypted_key.
        """
        return unhexlify(decrypt_totp_key(self.encrypted_key).encode())
