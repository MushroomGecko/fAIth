import json
from urllib.parse import urlencode

from asgiref.sync import sync_to_async
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.shortcuts import redirect
from django.urls import reverse

from backend.utils.authentication import (
    INVALID_CODE_MESSAGE,
    clear_unconfirmed_totp,
    confirm_device,
    create_recovery_codes,
    create_totp_device,
    enrollment_details,
    render_async,
    unconfirmed_totp_by_device_id,
    users_matching_username,
)
from backend.utils.login import get_next_url

# Session keys for the signup enrollment that is waiting for the user to confirm their authenticator app.
PENDING_DEVICE_SESSION_KEY = "pending_totp_device_id"
PENDING_CODES_SESSION_KEY = "pending_recovery_codes"

# Hidden form value that tells POST /signup the user is confirming the authenticator step.
ENROLLMENT_STEP = "authenticate"

# Hidden form value that tells POST /signup the user is skipping the authenticator step.
SKIP_STEP = "skip"


class SignupForm(UserCreationForm):
    """
    The account creation form. A username that differs from an existing one only in letter case is taken.
    """

    def clean_username(self):
        """
        Check that no account already uses this username, ignoring letter case.

        Django calls this during form.is_valid(), after the username field's own checks have passed.

        Returns:
            str: The username, unchanged.

        Raises:
            ValidationError: If an account already uses this name in any letter case.
        """
        username = self.cleaned_data["username"]
        # The database unique check is case-sensitive, so check case-insensitively here.
        if users_matching_username(username).exists():
            raise ValidationError("Username unavailable.")
        return username


def save_user_with_username_lock(form):
    """
    Save the user while holding a PostgreSQL advisory lock on the lowercased username.

    The lock is taken inside a transaction and released when it commits. A signup for a name that differs
    only in letter case waits at the lock, then finds this user in the re-check. The lock is held by the
    database, so it works across processes, including when the app runs more than one worker.

    Parameters:
        form (SignupForm): The validated signup form.

    Returns:
        User: The saved user.

    Raises:
        ValidationError: If an account with the same name in any letter case exists once the lock is held.
    """
    username = form.cleaned_data["username"]
    with transaction.atomic():
        # SQLite, used by the tests, has no advisory locks. The re-check below still runs there.
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [username.lower()])
        if users_matching_username(username).exists():
            raise ValidationError("Username unavailable.")
        return form.save()


async def create_user_and_devices(form):
    """
    Save the user, create an unconfirmed TOTP device, and create a confirmed recovery-code device.

    Parameters:
        form (UserCreationForm): The validated signup form.

    Returns:
        tuple[TOTPDevice, list[str]]: The new TOTP device and the plain-text recovery codes.
    """
    # Save under the username lock. The database calls are blocking, so this runs in a thread.
    user = await sync_to_async(save_user_with_username_lock, thread_sensitive=True)(form)
    totp = await create_totp_device(user)
    # Recovery codes are confirmed right away. Only the authenticator app waits for confirmation.
    codes = await create_recovery_codes(user, confirmed=True)
    return totp, codes


async def pending_device(device_id):
    """
    Return the unconfirmed TOTP device for this enrollment.

    Parameters:
        device_id (int | None): The ID of the pending TOTP device, from the session.

    Returns:
        TOTPDevice | None: The unconfirmed device, or None if there is none.
    """
    # Only unconfirmed devices count as pending. A confirmed device has already finished enrollment.
    return await unconfirmed_totp_by_device_id(device_id)


async def store_pending_device(session, device_id, codes):
    """
    Remember the pending enrollment for this browser session until it's confirmed.

    Parameters:
        session (SessionBase): The request's session.
        device_id (int): The ID of the unconfirmed TOTP device.
        codes (list[str]): The recovery codes generated for this enrollment.
    """
    # Store the pending device, and the codes encrypted, so the enrollment page still works after a page reload.
    await session.aset(PENDING_DEVICE_SESSION_KEY, device_id)
    await session.aset(PENDING_CODES_SESSION_KEY, _session_cipher().encrypt(json.dumps(codes).encode()).decode("ascii"))


async def read_pending_device_id(session):
    """
    Read the pending TOTP device ID from the session.

    Parameters:
        session (SessionBase): The request's session.

    Returns:
        int | None: The pending device ID, or None if there is no pending enrollment.
    """
    return await session.aget(PENDING_DEVICE_SESSION_KEY)


def _session_cipher():
    """Return the Fernet cipher for the recovery codes kept in the session, built from RECOVERY_CODE_ENCRYPTION_KEY."""
    return Fernet(settings.RECOVERY_CODE_ENCRYPTION_KEY)


async def read_pending_codes(session):
    """
    Read the recovery codes generated for this enrollment.

    Parameters:
        session (SessionBase): The request's session.

    Returns:
        list[str]: The recovery codes, or an empty list if there are none.
    """
    token = await session.aget(PENDING_CODES_SESSION_KEY)
    if not token:
        return []
    try:
        return json.loads(_session_cipher().decrypt(token.encode("ascii")))
    except InvalidToken:
        # The key was changed, or the stored value was damaged. The codes can't be read, so treat them as gone.
        return []


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


def login_url_for(next_url):
    """
    Return the login page URL, keeping the page the user was trying to reach.

    Parameters:
        next_url (str): A safe local path to return to after login, or an empty string.

    Returns:
        str: The login URL, with "next" in the query string when next_url is set.
    """
    login_url = reverse("api:login")
    return f"{login_url}?{urlencode({'next': next_url})}" if next_url else login_url


async def render_authenticate(request, device, codes, template, status=200, error=None, next_url=""):
    """
    Render the authenticator setup step with the QR code, secret, and recovery codes.

    Parameters:
        request (HttpRequest): The current request.
        device (TOTPDevice): The unconfirmed TOTP device to enroll.
        codes (list[str] | None): The recovery codes to display, or None once they're no longer shown.
        template (str): The authenticator setup page template path, passed in by the view.
        status (int): The HTTP status code for the response (default: 200).
        error (str | None): An error message to display above the form (default: None).
        next_url (str): The page to return to after login, carried in a hidden form field (default: "").

    Returns:
        HttpResponse: The rendered authenticator setup page.
    """
    # The QR code and secret come from the device, so they're rebuilt on every render.
    details = await enrollment_details(device)
    context = {**details, "codes": codes, "error": error, "next": next_url}
    # The signup views are wrapped in never_cache, so this page is not stored by the browser.
    return await render_async(request, template, context, status=status)


async def confirm_enrollment(request, template):
    """
    Confirm the authenticator app with a code from the user's device.

    Parameters:
        request (HttpRequest): The current request, with the code in POST as "otp_token".
        template (str): The authenticator setup page template path, passed in by the view.

    Returns:
        HttpResponse: A redirect to login on success, otherwise the setup page with an error.
    """
    next_url = await get_next_url(request, default="")
    # If there's no pending enrollment in this session, send the user back to the start.
    device, codes = await load_pending_enrollment(request.session)
    if device is None:
        return redirect("api:signup")

    # Strip stray spaces so a code pasted with a trailing space still works.
    token = request.POST.get("otp_token", "").strip()
    if await confirm_device(device, token):
        # Enrollment is finished, so the recovery codes shouldn't stay in the session.
        await clear_pending_device(request.session)
        return redirect(login_url_for(next_url))

    return await render_authenticate(
        request, device, codes, template, status=400, error=INVALID_CODE_MESSAGE, next_url=next_url
    )


async def skip_enrollment(request):
    """
    Skip the authenticator step. The account keeps its password and recovery codes, but has no TOTP.

    The unconfirmed TOTP device is deleted, so the account can log in with the password alone.
    The recovery codes are kept. Skipping is not an error, so it never blocks login.

    Parameters:
        request (HttpRequest): The current request.

    Returns:
        HttpResponse: A redirect to login, or back to the start if there is no pending enrollment.
    """
    device, _ = await load_pending_enrollment(request.session)
    if device is None:
        return redirect("api:signup")

    # Only the unconfirmed TOTP device is removed. The recovery codes stay on the account.
    await clear_unconfirmed_totp(device.user)
    # Forget the pending enrollment, so the recovery codes don't stay in the session.
    await clear_pending_device(request.session)
    return redirect(login_url_for(await get_next_url(request, default="")))


async def abandon_pending_enrollment(session):
    """
    Drop an unfinished authenticator step. The unconfirmed TOTP device is deleted, and the account has no TOTP.

    Parameters:
        session (SessionBase): The request's session.
    """
    device, _ = await load_pending_enrollment(session)
    if device is not None:
        await clear_unconfirmed_totp(device.user)
    await clear_pending_device(session)
