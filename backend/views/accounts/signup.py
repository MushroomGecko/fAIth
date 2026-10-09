import logging

from asgiref.sync import sync_to_async
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from ninja import Router

from backend.utils.signup import (
    ENROLLMENT_STEP,
    INVALID_CODE_MESSAGE,
    clear_pending_device,
    confirm_device,
    create_user_and_devices,
    enrollment_details,
    load_pending_enrollment,
    store_pending_device,
)
from fAIth.api_tags import APITags

# Set up logging
logger = logging.getLogger(__name__)

# Create router for ask selected API
router = Router()

SIGNUP_TEMPLATE = "registration/signup.html"
AUTHENTICATE_TEMPLATE = "registration/authenticate.html"


async def _render_authenticate(request, device, codes, status=200, error=None):
    """Render the authenticator setup step with the QR code, secret, and recovery codes."""
    details = enrollment_details(device)
    context = {**details, "codes": codes, "error": error}
    return await sync_to_async(render, thread_sensitive=True)(request, AUTHENTICATE_TEMPLATE, context, status=status)


async def _confirm_enrollment(request):
    """Confirm the authenticator app with a code from the user's device."""
    device, codes = await load_pending_enrollment(request.session)
    if device is None:
        return redirect("api:signup")

    token = request.POST.get("otp_token", "").strip()
    if await confirm_device(device, token):
        await clear_pending_device(request.session)
        return redirect("api:login")

    return await _render_authenticate(request, device, codes, status=400, error=INVALID_CODE_MESSAGE)


@router.get("/signup", tags=[APITags.BACKEND], url_name="signup")
async def signup_page(request):
    """Render the account creation form, or the authenticator step if an account is waiting on it."""
    device, codes = await load_pending_enrollment(request.session)
    if device is not None:
        return await _render_authenticate(request, device, codes)

    form = await sync_to_async(UserCreationForm, thread_sensitive=True)()
    return await sync_to_async(render, thread_sensitive=True)(request, SIGNUP_TEMPLATE, {"form": form})


@router.post("/signup", tags=[APITags.BACKEND])
async def signup(request):
    """Create an account and show the authenticator step, or confirm that step when the form says so."""
    if request.POST.get("step") == ENROLLMENT_STEP:
        return await _confirm_enrollment(request)

    form = await sync_to_async(UserCreationForm, thread_sensitive=True)(request.POST)
    is_valid = await sync_to_async(form.is_valid, thread_sensitive=True)()
    if not is_valid:
        return await sync_to_async(render, thread_sensitive=True)(
            request, SIGNUP_TEMPLATE, {"form": form}, status=400
        )

    totp, codes = await create_user_and_devices(form)
    await store_pending_device(request.session, totp.id, codes)
    return await _render_authenticate(request, totp, codes)
