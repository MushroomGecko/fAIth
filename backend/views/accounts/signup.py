import logging

from asgiref.sync import sync_to_async
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render
from ninja import Router

from backend.utils.signup import (
    ENROLLMENT_STEP,
    confirm_enrollment,
    create_user_and_devices,
    load_pending_enrollment,
    render_authenticate,
    store_pending_device,
)
from fAIth.api_tags import APITags

# Set up logging
logger = logging.getLogger(__name__)

# Create router for signup endpoints
router = Router()

SIGNUP_TEMPLATE = "registration/signup.html"


@router.get("/signup", tags=[APITags.BACKEND], url_name="signup")
async def signup_page(request):
    """
    Show the account creation form, or the authenticator setup step if an account is waiting on it.

    Parameters:
        request (HttpRequest): The current request.

    Returns:
        HttpResponse: The rendered signup page or authenticator setup page.
    """
    # If the user refreshes during enrollment, show the setup step again instead of a new form.
    device, codes = await load_pending_enrollment(request.session)
    if device is not None:
        return await render_authenticate(request, device, codes)

    form = await sync_to_async(UserCreationForm, thread_sensitive=True)()
    return await sync_to_async(render, thread_sensitive=True)(request, SIGNUP_TEMPLATE, {"form": form})


@router.post("/signup", tags=[APITags.BACKEND])
async def signup(request):
    """
    Create an account and show the authenticator setup step, or confirm that step when the form says so.

    Parameters:
        request (HttpRequest): The current request, with the form data in POST.

    Returns:
        HttpResponse: The authenticator setup page, a redirect after confirmation, or the signup page with errors.
    """
    # The authenticator step posts a hidden "step" value, so it's handled as confirmation, not signup.
    if request.POST.get("step") == ENROLLMENT_STEP:
        return await confirm_enrollment(request)

    # Build the signup form from the submitted data. Django's form.is_valid() runs the field checks and the password validators from AUTH_PASSWORD_VALIDATORS, so it's run in a thread.
    form = await sync_to_async(UserCreationForm, thread_sensitive=True)(request.POST)
    is_valid = await sync_to_async(form.is_valid, thread_sensitive=True)()

    # Show the form again with its errors. The 400 status tells the browser the submission was rejected, and nothing is created.
    if not is_valid:
        return await sync_to_async(render, thread_sensitive=True)(request, SIGNUP_TEMPLATE, {"form": form}, status=400)

    # Create the account and its unconfirmed devices, then show the setup step.
    totp, codes = await create_user_and_devices(form)
    await store_pending_device(request.session, totp.id, codes)
    return await render_authenticate(request, totp, codes)
