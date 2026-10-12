from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme

from backend.utils.authentication import confirmed_totp_device, render_async, users_matching_username


def get_next_url(request, default=None):
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
        str: The stored username if an account matches ignoring case, otherwise the input unchanged.
    """
    user = await users_matching_username(username).afirst()
    return user.username if user else username


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
    # Pass "next" back to the template so the form can post it along with the login.
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    return await render_async(request, template, {"form": form, "next": next_url}, status=status)
