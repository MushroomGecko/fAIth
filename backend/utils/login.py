from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme
from django_otp.plugins.otp_totp.models import TOTPDevice

# The login page template. render_login() is the only place that renders it.
LOGIN_TEMPLATE = "registration/login.html"


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
    user = await get_user_model().objects.filter(username__iexact=username).afirst()
    return user.username if user else username


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


async def delete_unconfirmed_totp(user):
    """
    Delete the user's unconfirmed TOTP device, if any. Recovery codes are not touched.

    Parameters:
        user (User): The user whose unfinished authenticator setup should be cleared.
    """
    await TOTPDevice.objects.filter(user=user, confirmed=False).adelete()


async def render_login(request, form, status=200):
    """
    Render the login form.

    Parameters:
        request (HttpRequest): The current request.
        form (OTPAuthenticationForm): The form to display, with any errors already attached.
        status (int): The HTTP status code for the response (default: 200).

    Returns:
        HttpResponse: The rendered login page.
    """
    # Pass "next" back to the template so the form can post it along with the login.
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    # Django's render() is synchronous, so run it in a thread to keep the event loop free.
    return await sync_to_async(render, thread_sensitive=True)(
        request, LOGIN_TEMPLATE, {"form": form, "next": next_url}, status=status
    )
