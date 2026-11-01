import asyncio
import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlparse

import segno
from asgiref.sync import sync_to_async
from axes.backends import AxesStandaloneBackend
from axes.handlers.proxy import AxesProxyHandler
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend, ModelBackend
from django.contrib.auth.signals import user_login_failed
from django.shortcuts import render
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from backend.models import EncryptedTOTPDevice
from backend.utils.hashing import username_hmac

# How many PBKDF2 iterations to run on each recovery code.
RECOVERY_CODE_HASH_ITERATIONS = 100000

# How many single-use recovery codes to create for each account.
RECOVERY_CODE_COUNT = 10

# How many random bytes each recovery code holds. 16 bytes is 128 bits, shown as 32 hex characters.
RECOVERY_CODE_BYTES = 16

# How many bytes of the PBKDF2 hash to keep. 12 bytes is 96 bits, which encodes to exactly 16 base64url characters,
# the most that StaticToken.token can hold.
RECOVERY_HASH_BYTES = 12

# Device names. The login device dropdown shows them, so they should read clearly.
TOTP_DEVICE_NAME = "Authenticator app"
RECOVERY_DEVICE_NAME = "Recovery code"

# Shown when the 6-digit code from an authenticator app is wrong during setup.
INVALID_CODE_MESSAGE = "That code wasn't valid. Check your authenticator app and try again."

# Shown on login and recovery while the account or this client is locked out after too many failed attempts.
# It doesn't say whose lock it is or how many attempts were counted, so it reveals nothing extra.
LOCKED_OUT_MESSAGE = "Too many failed attempts. You're locked out for 15 minutes, so please wait before trying again."


async def hash_recovery_code(code, device):
    """
    Hash one recovery code with PBKDF2 and keep 96 bits of it, encoded to fit StaticToken.token.

    The salt is built from the device's primary key. It isn't secret, it only needs to be unique
    per device. PBKDF2 is CPU-bound, so it runs in a worker thread and doesn't block the event loop.

    Parameters:
        code (str): The recovery code, as the user typed it or as it was generated.
        device (StaticDevice): The recovery-code device the code belongs to.

    Returns:
        str: The hash as 16 base64url characters (96 bits).
    """
    # Normalize first. Codes are shown lowercase with dashes, so a typed code is lowercased and the dashes and
    # spaces are removed before hashing. Then "3fa2c9d1-07b4" and "3fa2c9d107b4" hash to the same value.
    normalized = "".join(code.split()).replace("-", "").lower()
    salt = str(device.pk)
    digest = await asyncio.to_thread(
        hashlib.pbkdf2_hmac, "sha256", normalized.encode(), salt.encode(), RECOVERY_CODE_HASH_ITERATIONS
    )
    return base64.urlsafe_b64encode(digest[:RECOVERY_HASH_BYTES]).decode("ascii")


async def verify_recovery_code(device, code):
    """
    Check a recovery code and use it up if it's valid.

    Each code can be used once. The delete is a single query, so two requests can't both use the same code.

    There is no device-wide throttle. A device-level counter would be shared by every caller, so anyone with a
    username could lock the real user out of recovery. Limits are per username and client, and per client, through
    axes instead (see AXES_LOCKOUT_PARAMETERS in settings).

    Parameters:
        device (StaticDevice): The confirmed recovery-code device for the user.
        code (str): The recovery code the user typed.

    Returns:
        bool: True if the code was valid and has now been used up, otherwise False.
    """
    hashed = await hash_recovery_code(code, device)
    # Deleting the matching token both checks and uses it. The count tells us whether it matched.
    deleted, _ = await StaticToken.objects.filter(device=device, token=hashed).adelete()
    if not deleted:
        return False

    await sync_to_async(device.set_last_used_timestamp, thread_sensitive=True)()
    return True


async def new_recovery_code():
    """
    Return a new random recovery code of 128 bits, as 32 lowercase hex characters in four dash-separated groups.

    Returns:
        str: The code to show the user once, for example "3fa2c9d1-07b4e8a5-6c1d0f93-b2e75a48".
    """
    code = secrets.token_hex(RECOVERY_CODE_BYTES)
    return "-".join(code[i : i + 8] for i in range(0, len(code), 8))


async def create_recovery_codes(user, confirmed):
    """
    Create a recovery-code device for the user with new random codes. Only hashes are stored.

    Parameters:
        user (User): The user the codes belong to.
        confirmed (bool): Whether the device is confirmed. Signup and replacing codes both create it confirmed,
            since only the authenticator app waits for confirmation.

    Returns:
        list[str]: The plain-text recovery codes, to show the user one time.
    """
    device = await StaticDevice.objects.acreate(user=user, name=RECOVERY_DEVICE_NAME, confirmed=confirmed)
    codes = [await new_recovery_code() for _ in range(RECOVERY_CODE_COUNT)]
    # Each PBKDF2 hash runs in its own worker thread, so the codes are hashed in parallel.
    hashes = await asyncio.gather(*(hash_recovery_code(code, device) for code in codes))
    # Save all the hashed codes in one query instead of one query per code.
    await StaticToken.objects.abulk_create([StaticToken(device=device, token=token) for token in hashes])
    return codes


async def create_totp_device(user):
    """
    Create an unconfirmed authenticator app device for the user.

    Parameters:
        user (User): The user the device belongs to.

    Returns:
        EncryptedTOTPDevice: The new unconfirmed device, to be confirmed with a code from the user's app.
    """
    return await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=False)


async def confirmed_totp_device(user):
    """
    Return the user's confirmed authenticator app device, or None if they have none.

    Parameters:
        user (User): The user to look up.

    Returns:
        EncryptedTOTPDevice | None: The oldest confirmed device, if any.
    """
    return await EncryptedTOTPDevice.objects.filter(user=user, confirmed=True).order_by("id").afirst()


async def confirmed_recovery_device(user):
    """
    Return the user's confirmed recovery-code device, or None if they have none.

    Parameters:
        user (User): The user to look up.

    Returns:
        StaticDevice | None: The recovery-code device, if any.
    """
    return await StaticDevice.objects.filter(user=user, name=RECOVERY_DEVICE_NAME, confirmed=True).afirst()


async def _unconfirmed_totp_devices():
    """
    Return the queryset of unconfirmed authenticator app devices.

    Every unconfirmed lookup starts here, so the confirmed=False filter can't be left out by a caller.

    Returns:
        QuerySet: Unconfirmed TOTP devices, oldest first, with the user loaded.
    """
    return EncryptedTOTPDevice.objects.filter(confirmed=False).select_related("user").order_by("id")


async def unconfirmed_totp_by_user(user):
    """
    Return the user's unfinished authenticator app setup, or None if there isn't one.

    The user must be the logged-in user (request.user), never a value taken from request data.

    Parameters:
        user (User): The logged-in user to look up.

    Returns:
        EncryptedTOTPDevice | None: The oldest unconfirmed device, if any.
    """
    return await (await _unconfirmed_totp_devices()).filter(user=user).afirst()


async def unconfirmed_totp_by_device_id(device_id):
    """
    Return the unfinished authenticator app setup with this ID, or None if there isn't one.

    Only signup uses this, because its session stores the device ID before the user is logged in.
    The ID must come from the server-side session, never from request data.

    Parameters:
        device_id (int | None): The device ID from the session.

    Returns:
        EncryptedTOTPDevice | None: The unconfirmed device, or None if the ID is missing or not unconfirmed.
    """
    if device_id is None:
        return None
    return await (await _unconfirmed_totp_devices()).filter(id=device_id).afirst()


def users_matching_username(username):
    """
    Return a queryset of the accounts whose username matches, ignoring letter case.

    The username column holds an HMAC of the lowercase name, so the typed name is hashed before the lookup. Signup
    stops two usernames from differing only in case, so at most one account matches.

    Parameters:
        username (str): The username to match, as typed.

    Returns:
        QuerySet: The matching accounts. Callers add .aexists(), .afirst(), or .exists() as needed.
    """
    return get_user_model().objects.filter(username=username_hmac(username))


async def clear_unconfirmed_totp(user):
    """
    Delete the user's unfinished authenticator app setup, if any. Confirmed devices and recovery codes are not touched.

    Called when the user leaves the Security setup, opens their profile, or logs in.

    Parameters:
        user (User): The user whose unfinished setup should be cleared.
    """
    await EncryptedTOTPDevice.objects.filter(user=user, confirmed=False).adelete()


async def enrollment_details(device):
    """
    Return the QR code as inline SVG and the base32 secret for manual entry.

    Both are generated on the server from the device's otpauth URL. The QR code is drawn in a worker
    thread, since it is CPU-bound work.

    Parameters:
        device (EncryptedTOTPDevice): The TOTP device to enroll.

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
    Confirm the TOTP device if the token is valid. Recovery codes are not touched, since they are confirmed
    when they are created.

    Used by both signup and the account page.

    Parameters:
        device (EncryptedTOTPDevice): The unconfirmed TOTP device to check the token against.
        token (str): The 6-digit code from the user's authenticator app.

    Returns:
        bool: True if the token was valid and the device is now confirmed, otherwise False.
    """
    # verify_token saves throttling state to the database, so it runs in a thread.
    if not await sync_to_async(device.verify_token, thread_sensitive=True)(token):
        return False
    # Mark the authenticator app as confirmed. Only confirmed devices can be used to log in.
    device.confirmed = True
    await device.asave(update_fields=["confirmed"])
    return True


class AxesLockoutBackend(AxesStandaloneBackend, BaseBackend):
    """
    django-axes' lockout backend, with the async entry point that Django 6's aauthenticate() calls.

    AxesStandaloneBackend only defines the synchronous authenticate(). BaseBackend supplies aauthenticate(),
    which runs authenticate() in a thread. A locked-out login raises AxesBackendPermissionDenied, which
    Django's authenticate() catches, so the login is refused.
    """

    def get_user(self, user_id):
        """
        Load the logged-in user for a session. This backend is first in AUTHENTICATION_BACKENDS, so Django's
        force_login() stores it in the session. Without this method, BaseBackend would return None and the
        user would be logged out on the next request. ModelBackend does the actual lookup.
        """
        return ModelBackend().get_user(user_id)


async def account_locked(request, username):
    """
    Return True if django-axes has locked this client after too many failed attempts.

    The lock is per client, so failures against any account from this IP count toward it.

    Parameters:
        request (HttpRequest): The current request, which django-axes needs to read the client details.
        username (str): The username being tried. It doesn't change the lock, since the lock is per client.

    Returns:
        bool: True while this client is locked out.
    """
    return not await sync_to_async(AxesProxyHandler.is_allowed, thread_sensitive=True)(request, {"username": username})


async def record_failed_login(request, username):
    """
    Count a failed login or recovery attempt from this client, so django-axes can lock the client out after too many.

    Django's authenticate() already reports a wrong password. Use this for failures it can't see, such as a
    wrong authenticator or recovery code after the password was accepted.

    Parameters:
        request (HttpRequest): The current request.
        username (str): The plain username as the user typed it, or as shown by User.decrypted_username.
    """
    await sync_to_async(user_login_failed.send, thread_sensitive=True)(
        sender=get_user_model(), credentials={"username": username}, request=request
    )


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
