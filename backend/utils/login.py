from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme
from django_otp.forms import OTPAuthenticationForm

from backend.utils.authentication import (
    LOCKED_OUT_MESSAGE,
    confirmed_totp_device,
    render_async,
    users_matching_username,
)

# Shown for every failed login after the username is known: a wrong username or password, a wrong or
# missing authenticator code, and a code sent to an account without one. Because it is the same for all of
# them, it doesn't reveal whether the account exists or has an authenticator app.
INVALID_LOGIN_MESSAGE = (
    "The username, password, or authenticator code is incorrect. Usernames and passwords may be case-sensitive. "
    "If you use an authenticator app, check that the code is current and that it is set up on your account."
)


async def get_next_url(request, default=None):
    """
    Return the page to send the user to after login or logout.

    Uses the "next" value from the form or the query string if it is a safe local path. Otherwise
    falls back to default, so external URLs are never used.

    Parameters:
        request (HttpRequest): The current request.
        default (str | None): The fallback path. Defaults to settings.LOGIN_REDIRECT_URL.

    Returns:
        str: A local URL path to redirect to.
    """
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return next_url
    return default if default is not None else settings.LOGIN_REDIRECT_URL


async def canonical_username(username):
    """
    Return the stored spelling of a username, matched without regard to letter case.

    Signup stops two usernames from differing only in case, so at most one account matches.

    Parameters:
        username (str): The username as the user typed it.

    Returns:
        str: The username as the account stored it, decrypted, if an account matches ignoring case, otherwise the
            input unchanged.
    """
    user = await users_matching_username(username).afirst()
    return user.decrypted_username if user else username


async def authenticator_device_id(user):
    """
    Return the persistent ID of the user's confirmed authenticator app device.

    Parameters:
        user (User): The user whose authenticator device to look up.

    Returns:
        str | None: The device's persistent ID, or None if the user has no confirmed authenticator app.
    """
    # Only confirmed devices can be used to log in. The shared lookup returns the oldest one if there are several.
    device = await confirmed_totp_device(user)
    # The persistent ID is "<model>/<id>". The login form uses it to pick the device.
    return device.persistent_id if device else None


async def render_login(request, form, template, status=200):
    """
    Render the login form.

    Parameters:
        request (HttpRequest): The current request.
        form (OTPAuthenticationForm): The form to display, with any errors already attached.
        template (str): The login page template path, passed in by the view.
        status (int): The HTTP status code for the response (default: 200).

    Returns:
        HttpResponse: The rendered login page.
    """
    # Pass "next" back to the template so the form can post it along with the login. Only a safe local path is passed on.
    next_url = await get_next_url(request, default="")
    return await render_async(request, template, {"form": form, "next": next_url}, status=status)


async def login_locked(request, template):
    """
    Return the login page with the lockout message. Used while this client is locked out.

    The form is unbound, so django-otp doesn't validate anything and no password is checked.

    Parameters:
        request (HttpRequest): The current request.
        template (str): The login page template path, passed in by the view.

    Returns:
        HttpResponse: The login page with the lockout message, status 429.
    """
    form = await sync_to_async(OTPAuthenticationForm, thread_sensitive=True)(request)
    # add_error() expects cleaned_data, which an unbound form doesn't have. Nothing was validated, so an empty dict is correct.
    form.cleaned_data = {}
    form.add_error(None, LOCKED_OUT_MESSAGE)
    return await render_login(request, form, template, status=429)


async def login_refused(request, template, username):
    """
    Return the login page for a wrong username or password, with Django's generic login error.

    The form is unbound, so its clean() doesn't run authenticate() again. aauthenticate() has already
    counted this attempt, and a second count would lock this client out after three tries instead of five.

    Parameters:
        request (HttpRequest): The current request.
        template (str): The login page template path, passed in by the view.
        username (str): The username as typed, so the user doesn't have to retype it.

    Returns:
        HttpResponse: The login page with the generic login error, status 400.
    """
    form = await sync_to_async(OTPAuthenticationForm, thread_sensitive=True)(request, initial={"username": username})
    form.cleaned_data = {}
    form.add_error(None, INVALID_LOGIN_MESSAGE)
    return await render_login(request, form, template, status=400)
