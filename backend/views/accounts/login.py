from asgiref.sync import sync_to_async
from django.contrib.auth import aauthenticate, alogin
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect
from django_otp.forms import OTPAuthenticationForm
from ninja import Router

from backend.utils.authentication import clear_unconfirmed_totp
from backend.utils.login import (
    authenticator_device_id,
    canonical_username,
    get_next_url,
    render_login,
)
from backend.utils.signup import clear_pending_device
from fAIth.api_tags import APITags

# The login page template, rendered by the login views.
LOGIN_TEMPLATE = "registration/login.html"

# Create router for login endpoints
router = Router()


@router.get("/login/", tags=[APITags.BACKEND], url_name="login")
async def login_page(request):
    """
    Show the login form.

    Parameters:
        request (HttpRequest): The current request.

    Returns:
        HttpResponse: The rendered login page.
    """
    # An unbound form, so the page starts empty with no errors.
    form = await sync_to_async(OTPAuthenticationForm, thread_sensitive=True)(request)
    return await render_login(request, form, LOGIN_TEMPLATE)


@router.post("/login/", tags=[APITags.BACKEND])
@csrf_protect
async def login(request):
    """
    Log in with username, password, and an authenticator app code in one request.

    Parameters:
        request (HttpRequest): The current request, with the login form data in POST.

    Returns:
        HttpResponse: A redirect to the main site on success, otherwise the login page with errors.
    """
    # Usernames ignore letter case, so use the stored spelling. Then the password check finds the account.
    data = request.POST.copy()
    data["username"] = await canonical_username(data.get("username", ""))

    # The device depends on the user, so check the password first to find out who is logging in.
    user = await aauthenticate(
        request,
        username=data["username"],
        password=data.get("password", ""),
    )

    # An account with no confirmed authenticator app is a non-TOTP account, so the password is the whole login.
    # Unconfirmed devices from an unfinished signup are ignored.
    if user is not None and not await authenticator_device_id(user):
        if request.POST.get("otp_token", "").strip():
            # The password is right, but this account has no authenticator, so any code is an error.
            form = await sync_to_async(OTPAuthenticationForm, thread_sensitive=True)(request, data)
            await sync_to_async(form.is_valid, thread_sensitive=True)()
            # The form adds "Please select a device." here because this user has no device. Replace it with our message.
            form.errors.clear()
            form.add_error(None, "TOTP not set up or wrong code entered.")
            return await render_login(request, form, LOGIN_TEMPLATE, status=400)
        # The login succeeded, so an unfinished authenticator setup is over. Clear it, like signup does.
        await clear_unconfirmed_totp(user)
        # The pending recovery codes are plain text in the session. Drop them before alogin keeps the session.
        await clear_pending_device(request.session)
        await alogin(request, user)
        return redirect(await get_next_url(request))

    # The server always sets the device to the user's authenticator app. The browser can't choose
    # a recovery-code device, and recovery codes are never checked at login.
    data["otp_device"] = (await authenticator_device_id(user) or "") if user else ""

    # Validate the code against that device. The form also checks the password again.
    form = await sync_to_async(OTPAuthenticationForm, thread_sensitive=True)(request, data)
    is_valid = await sync_to_async(form.is_valid, thread_sensitive=True)()
    if is_valid:
        # Logging in with a code also ends any unfinished setup, the same as a password-only login.
        logged_in_user = form.get_user()
        await clear_unconfirmed_totp(logged_in_user)
        # The pending recovery codes are plain text in the session. Drop them before alogin keeps the session.
        await clear_pending_device(request.session)
        # clean_otp() sets user.otp_device, and django-otp's login signal marks the session as verified.
        await alogin(request, logged_in_user)
        return redirect(await get_next_url(request))
    return await render_login(request, form, LOGIN_TEMPLATE, status=400)
