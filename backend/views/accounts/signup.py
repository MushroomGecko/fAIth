import logging

from asgiref.sync import sync_to_async
from django.db import IntegrityError
from django.views.decorators.cache import never_cache
from ninja import Router

from backend.utils.authentication import render_async
from backend.utils.signup import (
    ENROLLMENT_STEP,
    SKIP_STEP,
    SignupForm,
    abandon_pending_enrollment,
    confirm_enrollment,
    create_user_and_devices,
    render_authenticate,
    skip_enrollment,
    store_pending_device,
)
from fAIth.api_tags import APITags

SIGNUP_TEMPLATE = "registration/signup.html"
# The authenticator setup page template, shown after the account is created.
AUTHENTICATE_TEMPLATE = "registration/authenticate.html"

# Set up logging
logger = logging.getLogger(__name__)

# Create router for signup endpoints
router = Router()


@router.get("/signup/", tags=[APITags.BACKEND], url_name="signup")
@never_cache
async def signup_page(request):
    """
    Show a fresh account creation form. Any unfinished authenticator step from earlier is abandoned.

    Parameters:
        request (HttpRequest): The current request.

    Returns:
        HttpResponse: The rendered signup page.
    """
    # Leaving the authenticator step without confirming it means no TOTP, so a new signup starts from scratch.
    await abandon_pending_enrollment(request.session)

    form = await sync_to_async(SignupForm, thread_sensitive=True)()
    return await render_async(request, SIGNUP_TEMPLATE, {"form": form})


@router.post("/signup/", tags=[APITags.BACKEND])
@never_cache
async def signup(request):
    """
    Create an account and show the authenticator setup step, or confirm or skip that step when the form says so.

    Parameters:
        request (HttpRequest): The current request, with the form data in POST.

    Returns:
        HttpResponse: The authenticator setup page, a redirect after confirmation or skip, or the signup page with errors.
    """
    # The authenticator step posts a hidden "step" value, so it's handled as confirmation or skip, not signup.
    step = request.POST.get("step")
    if step == ENROLLMENT_STEP:
        return await confirm_enrollment(request, AUTHENTICATE_TEMPLATE)
    if step == SKIP_STEP:
        return await skip_enrollment(request)

    # Build the signup form from the submitted data. Django's form.is_valid() runs the field checks and the password validators from AUTH_PASSWORD_VALIDATORS, so it's run in a thread.
    form = await sync_to_async(SignupForm, thread_sensitive=True)(request.POST)
    is_valid = await sync_to_async(form.is_valid, thread_sensitive=True)()

    # Show the form again with its errors. The 400 status tells the browser the submission was rejected, and nothing is created.
    if not is_valid:
        return await render_async(request, SIGNUP_TEMPLATE, {"form": form}, status=400)

    # Create the account and its unconfirmed devices, then show the setup step.
    try:
        totp, codes = await create_user_and_devices(form)
    except IntegrityError:
        # Another request saved the same username after the check above. Show the form again instead of a 500.
        form.add_error("username", "A user with that username already exists.")
        return await render_async(request, SIGNUP_TEMPLATE, {"form": form}, status=400)
    await store_pending_device(request.session, totp.id, codes)
    return await render_authenticate(request, totp, codes, AUTHENTICATE_TEMPLATE)
