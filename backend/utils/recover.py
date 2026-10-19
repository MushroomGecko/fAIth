from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

from backend.utils.account import PasswordForm, replace_recovery_codes, turn_off_totp
from backend.utils.authentication import create_totp_device, render_async
from backend.utils.signup import store_pending_device

# Shown for every failed recovery attempt, whatever the reason. It never says which field was wrong, whether
# the username exists, or whether the new password was rejected, so the page reveals nothing about the account.
INVALID_RECOVERY_MESSAGE = (
    "The password could not be reset. Check your username, recovery code, and new passwords, then try again."
)


async def blank_recovery_user():
    """
    Return an unsaved user, used for the password form when no account matches the username.

    Returns:
        User: An unsaved user with no username or password.
    """
    return get_user_model()()


async def recovery_password_form(user, data=None):
    """
    Build the new-password form for the account being recovered.

    Parameters:
        user (User): The account whose password will change, or an unsaved stand-in.
        data (QueryDict | None): The submitted POST data. None builds an unbound form.

    Returns:
        PasswordForm: The form, ready to validate or render.
    """
    return await sync_to_async(PasswordForm, thread_sensitive=True)(user, data)


async def reset_second_factor(user, session):
    """
    After a recovery, rotate the recovery codes and turn off the authenticator app. The user then
    chooses on the next page whether to set the authenticator app up again or skip it.

    The new codes are saved right away, and the old ones stop working. A new unconfirmed authenticator
    device is created and stored as the pending enrollment, so the setup step can confirm or skip it
    the same way signup does.

    Parameters:
        user (User): The user who just recovered the account.
        session (SessionBase): The request's session, where the pending enrollment is kept.

    Returns:
        tuple[TOTPDevice, list[str]]: The new unconfirmed authenticator device and the new plain-text recovery codes.
    """
    await turn_off_totp(user)
    codes = await replace_recovery_codes(user)
    totp = await create_totp_device(user)
    await store_pending_device(session, totp.id, codes)
    return totp, codes


async def render_recovery_page(request, template, form, username="", error=None, status=200):
    """
    Render the single recovery page with its form and any error.

    Parameters:
        request (HttpRequest): The current request.
        template (str): The template to render.
        form (PasswordForm): The bound or unbound password form.
        username (str): The username to fill back into the form.
        error (str | None): A message for the username/code check, if it failed.
        status (int): The HTTP status code to return.

    Returns:
        HttpResponse: The rendered recovery page.
    """
    context = {"form": form, "username": username, "error": error}
    return await render_async(request, template, context, status=status)


async def recovery_failed(request, template, username):
    """
    Return the one response used for every failed recovery attempt. The form is unbound, so no field errors show.

    Parameters:
        request (HttpRequest): The current request.
        template (str): The recovery page template path, passed in by the view.
        username (str): The username as typed, so the user doesn't have to retype it.

    Returns:
        HttpResponse: The recovery page with the generic error, status 400.
    """
    form = await recovery_password_form(await blank_recovery_user())
    return await render_recovery_page(
        request, template, form, username=username, error=INVALID_RECOVERY_MESSAGE, status=400
    )
