from urllib.parse import parse_qs, urlparse

import segno
from asgiref.sync import sync_to_async
from django.shortcuts import redirect, render
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from backend.utils.authentication import hash_recovery_code

# How many single-use recovery codes to create for each new account.
RECOVERY_CODE_COUNT = 10

# Session keys for the signup enrollment that is waiting for the user to confirm their authenticator app.
PENDING_DEVICE_SESSION_KEY = "pending_totp_device_id"
PENDING_CODES_SESSION_KEY = "pending_recovery_codes"

# Hidden form value that tells POST /signup the user is confirming the authenticator step.
ENROLLMENT_STEP = "authenticate"
INVALID_CODE_MESSAGE = "That code wasn't valid. Check your authenticator app and try again."

# The authenticator setup page template. render_authenticate() is the only place that renders it.
AUTHENTICATE_TEMPLATE = "registration/authenticate.html"


def hash_recovery_codes(codes, device):
    """
    Hash a batch of recovery codes for one device. This is CPU-bound, so call it through sync_to_async.

    Parameters:
        codes (list[str]): The plain-text recovery codes.
        device (StaticDevice): The recovery-code device the codes belong to.

    Returns:
        list[str]: The truncated hashes, in the same order as the codes.
    """
    return [hash_recovery_code(code, device) for code in codes]


async def create_user_and_devices(form):
    """
    Save the user and create unconfirmed TOTP and recovery-code devices.

    Parameters:
        form (UserCreationForm): The validated signup form.

    Returns:
        tuple[TOTPDevice, list[str]]: The new TOTP device and the plain-text recovery codes.
    """
    # Django's form.save() has no async version, so run it in a thread.
    user = await sync_to_async(form.save, thread_sensitive=True)()
    # The device names appear in the login device dropdown, so they should read clearly.
    totp = await TOTPDevice.objects.acreate(user=user, name="Authenticator app", confirmed=False)
    static = await StaticDevice.objects.acreate(user=user, name="Recovery code", confirmed=False)
    # Generate the recovery codes once. They're returned here so they can be shown to the user one time.
    codes = [StaticToken.random_token() for _ in range(RECOVERY_CODE_COUNT)]
    # Hashing 10 codes at 100,000 iterations each is slow, so run it in a worker thread instead of blocking the event loop.
    hashed_codes = await sync_to_async(hash_recovery_codes, thread_sensitive=False)(codes, static)
    # Save all the codes in one query instead of one query per code.
    await StaticToken.objects.abulk_create(
        [StaticToken(device=static, token=hashed_code) for hashed_code in hashed_codes]
    )
    return totp, codes


async def pending_device(device_id):
    """
    Return the unconfirmed TOTP device for this enrollment.

    Parameters:
        device_id (int | None): The ID of the pending TOTP device, from the session.

    Returns:
        TOTPDevice | None: The unconfirmed device, or None if there is none.
    """
    # No enrollment is pending if the session has no device ID.
    if device_id is None:
        return None
    # Only unconfirmed devices count as pending. A confirmed device has already finished enrollment.
    return await TOTPDevice.objects.filter(id=device_id, confirmed=False).select_related("user").afirst()


async def confirm_device(device, token):
    """
    Confirm the TOTP device and recovery codes if the token is valid.

    Parameters:
        device (TOTPDevice): The unconfirmed TOTP device to check the token against.
        token (str): The 6-digit code from the user's authenticator app.

    Returns:
        bool: True if the token was valid and the devices are now confirmed, otherwise False.
    """
    # django-otp's verify_token has no async version, so run it in a thread.
    if not await sync_to_async(device.verify_token, thread_sensitive=True)(token):
        return False
    # Mark the authenticator app as confirmed. Only confirmed devices can be used to log in.
    device.confirmed = True
    await device.asave(update_fields=["confirmed"])
    # Confirming the authenticator also confirms the recovery codes, which were created at the same time.
    await StaticDevice.objects.filter(user_id=device.user_id, confirmed=False).aupdate(confirmed=True)
    return True


async def store_pending_device(session, device_id, codes):
    """
    Remember the pending enrollment for this browser session until it's confirmed.

    Parameters:
        session (SessionBase): The request's session.
        device_id (int): The ID of the unconfirmed TOTP device.
        codes (list[str]): The recovery codes generated for this enrollment.
    """
    # Store the pending device and codes, so the enrollment page still works after a page reload.
    await session.aset(PENDING_DEVICE_SESSION_KEY, device_id)
    await session.aset(PENDING_CODES_SESSION_KEY, codes)


async def read_pending_device_id(session):
    """
    Read the pending TOTP device ID from the session.

    Parameters:
        session (SessionBase): The request's session.

    Returns:
        int | None: The pending device ID, or None if there is no pending enrollment.
    """
    return await session.aget(PENDING_DEVICE_SESSION_KEY)


async def read_pending_codes(session):
    """
    Read the recovery codes generated for this enrollment.

    Parameters:
        session (SessionBase): The request's session.

    Returns:
        list[str]: The recovery codes, or an empty list if there are none.
    """
    return await session.aget(PENDING_CODES_SESSION_KEY) or []


async def load_pending_enrollment(session):
    """
    Return the pending TOTP device and recovery codes for this session.

    Parameters:
        session (SessionBase): The request's session.

    Returns:
        tuple[TOTPDevice | None, list[str]]: The pending device (or None) and its recovery codes.
    """
    device = await pending_device(await read_pending_device_id(session))
    return device, await read_pending_codes(session)


async def clear_pending_device(session):
    """
    Forget the pending enrollment once it's confirmed.

    Parameters:
        session (SessionBase): The request's session.
    """
    # Remove both keys, so the recovery codes don't stay in the session after enrollment.
    await session.apop(PENDING_DEVICE_SESSION_KEY, None)
    await session.apop(PENDING_CODES_SESSION_KEY, None)


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


async def render_authenticate(request, device, codes, status=200, error=None):
    """
    Render the authenticator setup step with the QR code, secret, and recovery codes.

    Parameters:
        request (HttpRequest): The current request.
        device (TOTPDevice): The unconfirmed TOTP device to enroll.
        codes (list[str] | None): The recovery codes to display, or None once they're no longer shown.
        status (int): The HTTP status code for the response (default: 200).
        error (str | None): An error message to display above the form (default: None).

    Returns:
        HttpResponse: The rendered authenticator setup page.
    """
    # The QR code and secret come from the device, so they're rebuilt on every render.
    details = enrollment_details(device)
    context = {**details, "codes": codes, "error": error}
    return await sync_to_async(render, thread_sensitive=True)(request, AUTHENTICATE_TEMPLATE, context, status=status)


async def confirm_enrollment(request):
    """
    Confirm the authenticator app with a code from the user's device.

    Parameters:
        request (HttpRequest): The current request, with the code in POST as "otp_token".

    Returns:
        HttpResponse: A redirect to login on success, otherwise the setup page with an error.
    """
    # If there's no pending enrollment in this session, send the user back to the start.
    device, codes = await load_pending_enrollment(request.session)
    if device is None:
        return redirect("api:signup")

    # Strip stray spaces so a code pasted with a trailing space still works.
    token = request.POST.get("otp_token", "").strip()
    if await confirm_device(device, token):
        # Enrollment is finished, so the recovery codes shouldn't stay in the session.
        await clear_pending_device(request.session)
        return redirect("api:login")

    return await render_authenticate(request, device, codes, status=400, error=INVALID_CODE_MESSAGE)
