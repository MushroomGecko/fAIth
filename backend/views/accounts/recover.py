import logging

from asgiref.sync import sync_to_async
from django.views.decorators.cache import never_cache
from ninja import Router

from backend.utils.authentication import (
    confirmed_recovery_device,
    users_matching_username,
    verify_recovery_code,
)
from backend.utils.recover import (
    INVALID_RECOVERY_MESSAGE,
    blank_recovery_user,
    recovery_password_form,
    render_recovery_page,
    reset_second_factor,
)
from backend.utils.signup import render_authenticate
from fAIth.api_tags import APITags

RECOVERY_TEMPLATE = "registration/recover.html"
# The authenticator setup step, shown after recovery so the user can set it up again or skip it.
AUTHENTICATE_TEMPLATE = "registration/authenticate.html"

# Set up logging
logger = logging.getLogger(__name__)

# Create router for recovery endpoints
router = Router()


@router.get("/recover/", tags=[APITags.BACKEND], url_name="recover")
@never_cache
async def recovery_page(request):
    """
    Show the recovery form: username, recovery code, and the new password.

    Parameters:
        request (HttpRequest): The current request.

    Returns:
        HttpResponse: The rendered recovery page.
    """
    form = await recovery_password_form(await blank_recovery_user())
    return await render_recovery_page(request, RECOVERY_TEMPLATE, form)


@router.post("/recover/", tags=[APITags.BACKEND])
@never_cache
async def recovery_submit(request):
    """
    Reset the password in one step. The new passwords are checked first, then the username and recovery code.
    The recovery code is only used up once the passwords are valid, so a typo in a password doesn't cost a code.

    On success the recovery codes are replaced and the authenticator app is turned off. The authenticator
    setup step is shown, where the user can set the app up again or skip it.

    Parameters:
        request (HttpRequest): The current request, with username, recovery_code, new_password1, and new_password2 in POST.

    Returns:
        HttpResponse: The authenticator setup step with the new recovery codes on success, or the recovery page with errors.
    """
    username = request.POST.get("username", "").strip()
    code = request.POST.get("recovery_code", "")

    user = await users_matching_username(username).afirst()

    # Check the new passwords first. Nothing is used up yet, so a password typo doesn't cost the user their code.
    form = await recovery_password_form(user or await blank_recovery_user(), request.POST)
    if not await sync_to_async(form.is_valid, thread_sensitive=True)():
        return await render_recovery_page(request, RECOVERY_TEMPLATE, form, username=username, status=400)

    # Then check the username and recovery code. A valid code is used up here, before the password is saved.
    device = await confirmed_recovery_device(user) if user is not None else None
    if device is None or not await verify_recovery_code(device, code):
        # Same message for a missing username and a wrong code.
        form = await recovery_password_form(await blank_recovery_user())
        return await render_recovery_page(
            request, RECOVERY_TEMPLATE, form, username=username, error=INVALID_RECOVERY_MESSAGE, status=400
        )

    # The password hash changes, so Django's session check signs out any other browser still holding this account.
    await sync_to_async(form.save, thread_sensitive=True)()

    # The old recovery codes are used up and the authenticator app is off, so issue new codes and let the user
    # set the app up again or skip it, the same way signup does.
    totp, codes = await reset_second_factor(user, request.session)
    return await render_authenticate(request, totp, codes, AUTHENTICATE_TEMPLATE)
