import logging

from asgiref.sync import sync_to_async
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from ninja import Router

from backend.utils.authentication import (
    account_locked,
    confirmed_recovery_device,
    record_failed_login,
    users_matching_username,
    verify_recovery_code,
)
from backend.utils.login import get_next_url
from backend.utils.recover import (
    blank_recovery_user,
    recovery_failed,
    recovery_locked,
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
    # Keep the "next" page from the login link so it can be passed on through recovery and back to login.
    next_url = await get_next_url(request, default="")
    return await render_recovery_page(request, RECOVERY_TEMPLATE, form, next_url=next_url)


@router.post("/recover/", tags=[APITags.BACKEND])
@csrf_protect
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
    next_url = await get_next_url(request, default="")
    username = request.POST.get("username", "").strip()
    code = request.POST.get("recovery_code", "")

    user = await users_matching_username(username).afirst()

    # Use the stored spelling of the username, so failures are recorded under the same name as the account.
    account_name = user.decrypted_username if user is not None else username
    # A locked client gets the lockout message and nothing else. No password or code is checked.
    if await account_locked(request, account_name):
        return await recovery_locked(request, RECOVERY_TEMPLATE, username, next_url=next_url)

    # Every failure below returns the same response, with no field-level errors. Otherwise the messages would
    # reveal whether the username exists, whether the code was wrong, or whether the new password matched the
    # current one.
    # Check the new passwords first. Nothing is used up yet, so a password typo doesn't cost the user their code.
    form = await recovery_password_form(user or await blank_recovery_user(), request.POST)
    if not await sync_to_async(form.is_valid, thread_sensitive=True)():
        # A bad new password counts against this client too, so repeated typos lock it out.
        await record_failed_login(request, account_name)
        return await recovery_failed(request, RECOVERY_TEMPLATE, username, next_url=next_url)

    # Then check the username and recovery code. A valid code is used up here, before the password is saved.
    device = await confirmed_recovery_device(user) if user is not None else None
    if device is None or not await verify_recovery_code(device, code):
        # A wrong code counts against this client, so repeated guesses lock it out.
        await record_failed_login(request, account_name)
        return await recovery_failed(request, RECOVERY_TEMPLATE, username, next_url=next_url)

    # The password hash changes, so Django's session check signs out any other browser still holding this account.
    await sync_to_async(form.save, thread_sensitive=True)()

    # The old recovery codes are used up and the authenticator app is off, so issue new codes and let the user
    # set the app up again or skip it, the same way signup does.
    totp, codes = await reset_second_factor(user, request.session)
    return await render_authenticate(request, totp, codes, AUTHENTICATE_TEMPLATE, next_url=next_url)
