import hashlib
from urllib.parse import parse_qs, urlparse

import segno
from asgiref.sync import sync_to_async
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

# How many PBKDF2 iterations to run on each recovery code.
RECOVERY_CODE_HASH_ITERATIONS = 100000

# Shown when the 6-digit code from an authenticator app is wrong during setup.
INVALID_CODE_MESSAGE = "That code wasn't valid. Check your authenticator app and try again."


def hash_recovery_code(code, device):
    """
    Hash one recovery code with PBKDF2 and truncate it to fit StaticToken.token.

    The salt is built from the device's primary key. It isn't secret, it only needs to be unique
    per device. This is CPU-bound, so call it through sync_to_async from async code.

    Parameters:
        code (str): The recovery code, as the user typed it or as it was generated.
        device (StaticDevice): The recovery-code device the code belongs to.

    Returns:
        str: The hash as 16 hex characters (64 bits).
    """
    # Normalize first. random_token() returns lowercase, so a typed code must match that form.
    normalized = code.strip().lower()
    salt = str(device.pk)
    digest = hashlib.pbkdf2_hmac("sha256", normalized.encode(), salt.encode(), RECOVERY_CODE_HASH_ITERATIONS)
    return digest.hex()[:16]


async def verify_recovery_code(device, code):
    """
    Check a recovery code and use it up if it's valid.

    Throttling works the same way as django-otp's static device. Failed attempts count toward
    the limit, and a successful one resets it. Each code can be used once. The delete is a
    single query, so two requests can't both use the same code.

    Parameters:
        device (StaticDevice): The confirmed recovery-code device for the user.
        code (str): The recovery code the user typed.

    Returns:
        bool: True if the code was valid and has now been used up, otherwise False.
    """
    # If too many recent attempts failed, refuse without checking the code.
    allowed, _ = await sync_to_async(device.verify_is_allowed, thread_sensitive=True)()
    if not allowed:
        return False

    hashed = await sync_to_async(hash_recovery_code, thread_sensitive=False)(code, device)
    # Deleting the matching token both checks and uses it. The count tells us whether it matched.
    deleted, _ = await StaticToken.objects.filter(device=device, token=hashed).adelete()
    if not deleted:
        await sync_to_async(device.throttle_increment, thread_sensitive=True)()
        return False

    await sync_to_async(device.throttle_reset, thread_sensitive=True)()
    await sync_to_async(device.set_last_used_timestamp, thread_sensitive=True)()
    return True


def clear_unconfirmed_totp(user):
    """
    Delete the user's unfinished authenticator app setup, if any. Confirmed devices and recovery codes are not touched.

    Called when the user leaves the Security setup, opens their profile, or logs in. It is synchronous,
    so async callers wrap it in sync_to_async.

    Parameters:
        user (User): The user whose unfinished setup should be cleared.
    """
    TOTPDevice.objects.filter(user=user, confirmed=False).delete()


def enrollment_details(device):
    """
    Return the QR code as inline SVG and the base32 secret for manual entry.

    Both are generated on the server from the device's otpauth URL. This is pure computation,
    so it stays synchronous.

    Parameters:
        device (TOTPDevice): The TOTP device to enroll.

    Returns:
        dict[str, str]: The inline SVG under "svg" and the base32 secret under "secret".
    """
    # The otpauth URL contains the secret and the account name. Authenticator apps read it from the QR code.
    config_url = device.config_url
    # The manual-entry secret is the "secret" parameter in that URL.
    secret = parse_qs(urlparse(config_url).query)["secret"][0]
    # Draw the QR code as SVG on the server, so no third-party script is needed.
    svg = segno.make(config_url, error="m").svg_inline(scale=5)
    return {"svg": svg, "secret": secret}


def confirm_device(device, token):
    """
    Confirm the TOTP device and its recovery codes if the token is valid.

    Used by both signup and the account page. It is synchronous, so async callers wrap it in sync_to_async.

    Parameters:
        device (TOTPDevice): The unconfirmed TOTP device to check the token against.
        token (str): The 6-digit code from the user's authenticator app.

    Returns:
        bool: True if the token was valid and the devices are now confirmed, otherwise False.
    """
    if not device.verify_token(token):
        return False
    # Mark the authenticator app as confirmed. Only confirmed devices can be used to log in.
    device.confirmed = True
    device.save(update_fields=["confirmed"])
    # Confirming the authenticator also confirms the recovery codes, which were created at the same time.
    StaticDevice.objects.filter(user_id=device.user_id, confirmed=False).update(confirmed=True)
    return True
