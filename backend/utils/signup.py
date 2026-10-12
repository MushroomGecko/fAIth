from asgiref.sync import sync_to_async
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.shortcuts import redirect

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
            raise ValidationError("A user with that username already exists.")
        return username


# Session keys for the signup enrollment that is waiting for the user to confirm their authenticator app.
PENDING_DEVICE_SESSION_KEY = "pending_totp_device_id"
PENDING_CODES_SESSION_KEY = "pending_recovery_codes"

# Hidden form value that tells POST /signup the user is confirming the authenticator step.
ENROLLMENT_STEP = "authenticate"

# Hidden form value that tells POST /signup the user is skipping the authenticator step.
SKIP_STEP = "skip"


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
    totp = await create_totp_device(user)
    codes = await create_recovery_codes(user, confirmed=False)
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


async def render_authenticate(request, device, codes, template, status=200, error=None):
    """
    Render the authenticator setup step with the QR code, secret, and recovery codes.

    Parameters:
        request (HttpRequest): The current request.
        device (TOTPDevice): The unconfirmed TOTP device to enroll.
        codes (list[str] | None): The recovery codes to display, or None once they're no longer shown.
        template (str): The authenticator setup page template path, passed in by the view.
        status (int): The HTTP status code for the response (default: 200).
        error (str | None): An error message to display above the form (default: None).

    Returns:
        HttpResponse: The rendered authenticator setup page.
    """
    # The QR code and secret come from the device, so they're rebuilt on every render.
    details = await enrollment_details(device)
    context = {**details, "codes": codes, "error": error}
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

    return await render_authenticate(request, device, codes, template, status=400, error=INVALID_CODE_MESSAGE)


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
    return redirect("api:login")


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
