from asgiref.sync import sync_to_async
from django.contrib.auth import aauthenticate, alogin
from django.shortcuts import redirect, render
from django_otp.forms import OTPAuthenticationForm
from ninja import Router

from backend.utils.authentication import authenticator_device_id
from fAIth.api_tags import APITags

router = Router()

LOGIN_TEMPLATE = "registration/login.html"


async def _render_login(request, form, status=200):
    """Render the login form."""
    return await sync_to_async(render, thread_sensitive=True)(request, LOGIN_TEMPLATE, {"form": form}, status=status)


@router.get("/login", tags=[APITags.BACKEND], url_name="login")
async def login_page(request):
    """Render the login form."""
    form = await sync_to_async(OTPAuthenticationForm, thread_sensitive=True)(request)
    return await _render_login(request, form)


@router.post("/login", tags=[APITags.BACKEND])
async def login(request):
    """Log in with username, password, and an authenticator app code in one request."""
    # The device depends on the user, so check the password first to find out who is logging in.
    user = await aauthenticate(
        request,
        username=request.POST.get("username", ""),
        password=request.POST.get("password", ""),
    )

    # The server always sets the device to the user's authenticator app. The browser can't choose
    # a recovery-code device, and recovery codes are never checked at login.
    data = request.POST.copy()
    data["otp_device"] = (await authenticator_device_id(user) or "") if user else ""

    form = await sync_to_async(OTPAuthenticationForm, thread_sensitive=True)(request, data)
    is_valid = await sync_to_async(form.is_valid, thread_sensitive=True)()
    if is_valid:
        # clean_otp() sets user.otp_device, and django-otp's login signal marks the session as verified.
        await alogin(request, form.get_user())
        return redirect("/")

    return await _render_login(request, form, status=400)
