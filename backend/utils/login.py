from asgiref.sync import sync_to_async
from django.shortcuts import render
from django_otp.plugins.otp_totp.models import TOTPDevice

# The login page template. render_login() is the only place that renders it.
LOGIN_TEMPLATE = "registration/login.html"


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
    # Django's render() is synchronous, so run it in a thread to keep the event loop free.
    return await sync_to_async(render, thread_sensitive=True)(request, LOGIN_TEMPLATE, {"form": form}, status=status)
