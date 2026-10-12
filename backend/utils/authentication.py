import hashlib
from urllib.parse import parse_qs, urlparse

import segno
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

# How many PBKDF2 iterations to run on each recovery code.
RECOVERY_CODE_HASH_ITERATIONS = 100000

# How many single-use recovery codes to create for each account.
RECOVERY_CODE_COUNT = 10

# Device names. The login device dropdown shows them, so they should read clearly.
TOTP_DEVICE_NAME = "Authenticator app"
RECOVERY_DEVICE_NAME = "Recovery code"

# Shown when the 6-digit code from an authenticator app is wrong during setup.
INVALID_CODE_MESSAGE = "That code wasn't valid. Check your authenticator app and try again."


def hash_recovery_code(code, device):
    """
    Hash one recovery code with PBKDF2 and truncate it to fit StaticToken.token.

    The salt is built from the device's primary key. It isn't secret, it only needs to be unique
    per device. This is CPU-bound, so async callers run it through sync_to_async.

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


async def create_recovery_codes(user, confirmed):
    """
    Create a recovery-code device for the user with new random codes. Only hashes are stored.

    Parameters:
        user (User): The user the codes belong to.
        confirmed (bool): Whether the device is confirmed. Signup creates it unconfirmed until the
            authenticator app is confirmed. Replacing codes creates it confirmed.

    Returns:
        list[str]: The plain-text recovery codes, to show the user one time.
    """
    device = await StaticDevice.objects.acreate(user=user, name=RECOVERY_DEVICE_NAME, confirmed=confirmed)
    codes = [StaticToken.random_token() for _ in range(RECOVERY_CODE_COUNT)]
    # Hashing is CPU-bound (PBKDF2), so all the codes are hashed together in one worker thread.
    hashes = await sync_to_async(lambda: [hash_recovery_code(code, device) for code in codes], thread_sensitive=False)()
    # Save all the hashed codes in one query instead of one query per code.
    await StaticToken.objects.abulk_create([StaticToken(device=device, token=token) for token in hashes])
    return codes


async def create_totp_device(user):
    """
    Create an unconfirmed authenticator app device for the user.

    Parameters:
        user (User): The user the device belongs to.

    Returns:
        TOTPDevice: The new unconfirmed device, to be confirmed with a code from the user's app.
    """
    return await TOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=False)


async def confirmed_totp_device(user):
    """
    Return the user's confirmed authenticator app device, or None if they have none.

    Parameters:
        user (User): The user to look up.

    Returns:
        TOTPDevice | None: The oldest confirmed device, if any.
    """
    return await TOTPDevice.objects.filter(user=user, confirmed=True).order_by("id").afirst()


def _unconfirmed_totp_devices():
    """
    Return the queryset of unconfirmed authenticator app devices.

    Every unconfirmed lookup starts here, so the confirmed=False filter can't be left out by a caller.

    Returns:
        QuerySet: Unconfirmed TOTP devices, oldest first, with the user loaded.
    """
    return TOTPDevice.objects.filter(confirmed=False).select_related("user").order_by("id")


async def unconfirmed_totp_by_user(user):
    """
    Return the user's unfinished authenticator app setup, or None if there isn't one.

    The user must be the logged-in user (request.user), never a value taken from request data.

    Parameters:
        user (User): The logged-in user to look up.

    Returns:
        TOTPDevice | None: The oldest unconfirmed device, if any.
    """
    return await _unconfirmed_totp_devices().filter(user=user).afirst()


async def unconfirmed_totp_by_device_id(device_id):
    """
    Return the unfinished authenticator app setup with this ID, or None if there isn't one.

    Only signup uses this, because its session stores the device ID before the user is logged in.
    The ID must come from the server-side session, never from request data.

    Parameters:
        device_id (int | None): The device ID from the session.

    Returns:
        TOTPDevice | None: The unconfirmed device, or None if the ID is missing or not unconfirmed.
    """
    if device_id is None:
        return None
    return await _unconfirmed_totp_devices().filter(id=device_id).afirst()


def users_matching_username(username):
    """
    Return a queryset of the accounts whose username matches, ignoring letter case.

    Signup stops two usernames from differing only in case, so at most one account matches.

    Parameters:
        username (str): The username to match.

    Returns:
        QuerySet: The matching accounts. Callers add .aexists(), .afirst(), or .exists() as needed.
    """
    return get_user_model().objects.filter(username__iexact=username)


async def clear_unconfirmed_totp(user):
    """
    Delete the user's unfinished authenticator app setup, if any. Confirmed devices and recovery codes are not touched.

    Called when the user leaves the Security setup, opens their profile, or logs in.

    Parameters:
        user (User): The user whose unfinished setup should be cleared.
    """
    await TOTPDevice.objects.filter(user=user, confirmed=False).adelete()


async def enrollment_details(device):
    """
    Return the QR code as inline SVG and the base32 secret for manual entry.

    Both are generated on the server from the device's otpauth URL. The QR code is drawn in a worker
    thread, since it is CPU-bound work.

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
    svg = await sync_to_async(lambda: segno.make(config_url, error="m").svg_inline(scale=5), thread_sensitive=False)()
    return {"svg": svg, "secret": secret}


async def confirm_device(device, token):
    """
    Confirm the TOTP device and its recovery codes if the token is valid.

    Used by both signup and the account page.

    Parameters:
        device (TOTPDevice): The unconfirmed TOTP device to check the token against.
        token (str): The 6-digit code from the user's authenticator app.

    Returns:
        bool: True if the token was valid and the devices are now confirmed, otherwise False.
    """
    # verify_token saves throttling state to the database, so it runs in a thread.
    if not await sync_to_async(device.verify_token, thread_sensitive=True)(token):
        return False
    # Mark the authenticator app as confirmed. Only confirmed devices can be used to log in.
    device.confirmed = True
    await device.asave(update_fields=["confirmed"])
    # Confirming the authenticator also confirms the recovery codes, which were created at the same time.
    await StaticDevice.objects.filter(user_id=device.user_id, confirmed=False).aupdate(confirmed=True)
    return True


async def render_async(request, template, context=None, status=200):
    """
    Render a template from async code. Django's render() is synchronous, so it runs in a thread.

    Parameters:
        request (HttpRequest): The current request.
        template (str): The template path, passed in by the view.
        context (dict | None): The template context. Defaults to none.
        status (int): The HTTP status code for the response (default: 200).

    Returns:
        HttpResponse: The rendered page.
    """
    return await sync_to_async(render, thread_sensitive=True)(request, template, context, status=status)
