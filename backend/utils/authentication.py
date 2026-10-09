import hashlib

from asgiref.sync import sync_to_async
from django_otp.plugins.otp_static.models import StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

# How many PBKDF2 iterations to run on each recovery code.
RECOVERY_CODE_HASH_ITERATIONS = 100000


async def authenticator_device_id(user):
    """
    Return the persistent ID of the user's confirmed authenticator app device.

    Parameters:
        user (User): The user whose authenticator device to look up.

    Returns:
        str | None: The device's persistent ID, or None if the user has no confirmed authenticator app.
    """
    # Only confirmed devices can be used to log in. The oldest one is used if there are several.
    device = await TOTPDevice.objects.filter(user=user, confirmed=True).order_by("id").afirst()
    # The persistent ID is "<model>/<id>". The login form uses it to pick the device.
    return device.persistent_id if device else None


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
