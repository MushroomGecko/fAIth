from django.conf import settings
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from ninja import Router

from backend.utils.account import (
    PasswordForm,
    UsernameForm,
    check_reauth,
    has_totp,
    replace_recovery_codes,
    section_context,
    security_context,
    start_totp_setup,
    turn_off_totp,
)
from backend.utils.authentication import (
    INVALID_CODE_MESSAGE,
    clear_unconfirmed_totp,
    confirm_device,
    unconfirmed_totp_by_user,
)
from fAIth.api_tags import APITags

# Create router for account endpoints
router = Router()

# The Account section partial, and the greeting that the username change swaps into the navbar.
ACCOUNT_SECTION_TEMPLATE = "profile/partials/settings.html"
GREETING_TEMPLATE = "profile/partials/greeting.html"
# The Security section partial, which holds the password, two-factor, and recovery key cards.
SECURITY_SECTION_TEMPLATE = "profile/partials/security.html"


@router.get("/profile/", tags=[APITags.BACKEND], url_name="profile")
@never_cache
@login_required
def account_page(request):
    """
    Show the profile page. Anonymous users are redirected to the login page.

    Opening the profile ends any unfinished two-factor setup, the same as leaving the Security section.
    """
    clear_unconfirmed_totp(request.user)
    return render(request, "profile/index.html")


@router.get("/profile/account/", tags=[APITags.BACKEND], url_name="profile_account")
@never_cache
@login_required
def account_section(request):
    """
    Show the Account section with the username form and the danger zone.

    Opening this section ends any unfinished two-factor setup. Clicking Account in the sidebar leaves Security,
    so the setup is dropped here.
    """
    clear_unconfirmed_totp(request.user)
    return render(request, ACCOUNT_SECTION_TEMPLATE, section_context(request))


@router.post("/profile/username/", tags=[APITags.BACKEND], url_name="profile_username")
@never_cache
@login_required
def change_username(request):
    """
    Change the logged-in user's username after confirming the password (and verification code if the
    account has an authenticator app).

    Parameters:
        request (HttpRequest): The current request, with username, password, and otp_token in POST.

    Returns:
        HttpResponse: The Account section, with the new greeting when the change succeeds. The status is 400
        when the password or code is wrong, or the name is rejected. The settings.js script swaps that response
        in, since HTMX skips 4xx by default.
    """
    form = UsernameForm(request.POST, instance=request.user)

    # Check the password and code first, so a wrong password never reveals whether the name is taken.
    auth_error = check_reauth(request.user, request.POST.get("password", ""), request.POST.get("otp_token", ""))
    if auth_error:
        return render(
            request,
            ACCOUNT_SECTION_TEMPLATE,
            section_context(request, form=form, username_auth_error=auth_error),
            status=400,
        )

    if not form.is_valid():
        return render(request, ACCOUNT_SECTION_TEMPLATE, section_context(request, form=form), status=400)

    form.save()
    # Update the account section and the greeting in the navbar. The greeting uses an out-of-band swap.
    section = render(request, ACCOUNT_SECTION_TEMPLATE, section_context(request, saved=True))
    greeting = render(request, GREETING_TEMPLATE)
    return HttpResponse(section.content + greeting.content)


@router.post("/profile/delete/", tags=[APITags.BACKEND], url_name="profile_delete")
@never_cache
@login_required
def delete_account(request):
    """
    Permanently delete the logged-in user's account after confirming the password (and verification code
    if the account has an authenticator app).

    Parameters:
        request (HttpRequest): The current request, with password and otp_token in POST.

    Returns:
        HttpResponse: A HX-Redirect to the main site after deletion. The status is 400 with an error message
        when the password or code is wrong.
    """
    auth_error = check_reauth(request.user, request.POST.get("password", ""), request.POST.get("otp_token", ""))
    if auth_error:
        return render(
            request, ACCOUNT_SECTION_TEMPLATE, section_context(request, delete_auth_error=auth_error), status=400
        )

    user = request.user
    logout(request)
    user.delete()
    # HX-Redirect makes HTMX load the main site as a full page, so the logged-out navbar shows.
    response = HttpResponse()
    response["HX-Redirect"] = settings.LOGOUT_REDIRECT_URL
    return response


@router.get("/profile/security/", tags=[APITags.BACKEND], url_name="profile_security")
@never_cache
@login_required
def security_section(request):
    """
    Show the Security section with the change password form.
    """
    return render(request, SECURITY_SECTION_TEMPLATE, security_context(request))


@router.post("/profile/password/", tags=[APITags.BACKEND], url_name="profile_password")
@never_cache
@login_required
def change_password(request):
    """
    Change the logged-in user's password after confirming the current password (and verification code if the
    account has an authenticator app).

    Parameters:
        request (HttpRequest): The current request, with password, otp_token, new_password1, and new_password2 in POST.

    Returns:
        HttpResponse: The Security section, with a success message when the change works. The status is 400 when
        the current password or code is wrong, or the new password is rejected. The settings.js script swaps that
        response in, since HTMX skips 4xx by default.
    """
    # Check the current password and code first, so a wrong password never shows feedback about the new one.
    auth_error = check_reauth(request.user, request.POST.get("password", ""), request.POST.get("otp_token", ""))
    if auth_error:
        return render(
            request,
            SECURITY_SECTION_TEMPLATE,
            security_context(request, password_auth_error=auth_error),
            status=400,
        )

    form = PasswordForm(request.user, request.POST)
    if not form.is_valid():
        return render(request, SECURITY_SECTION_TEMPLATE, security_context(request, password_form=form), status=400)

    form.save()
    # Changing the password invalidates the session. Keep this browser signed in with the new hash.
    update_session_auth_hash(request, request.user)
    return render(request, SECURITY_SECTION_TEMPLATE, security_context(request, password_saved=True))


@router.post("/profile/recovery-codes/", tags=[APITags.BACKEND], url_name="profile_recovery_codes")
@never_cache
@login_required
def refresh_recovery_codes(request):
    """
    Replace the logged-in user's recovery codes after confirming the password (and verification code if the
    account has an authenticator app).

    The new codes are saved before the response is sent, so they stay valid even if the user closes the page
    without clicking "I have written down my codes". The old codes stop working.

    Parameters:
        request (HttpRequest): The current request, with password and otp_token in POST.

    Returns:
        HttpResponse: The Security section, showing the new codes once. The status is 400 when the password or
        code is wrong. The settings.js script swaps that response in, since HTMX skips 4xx by default.
    """
    auth_error = check_reauth(request.user, request.POST.get("password", ""), request.POST.get("otp_token", ""))
    if auth_error:
        return render(
            request,
            SECURITY_SECTION_TEMPLATE,
            security_context(request, recovery_auth_error=auth_error),
            status=400,
        )

    codes = replace_recovery_codes(request.user)
    # This response shows the plain-text codes. The never_cache decorator keeps browsers and proxies from storing it.
    return render(request, SECURITY_SECTION_TEMPLATE, security_context(request, recovery_codes=codes))


@router.post("/profile/totp/enable/", tags=[APITags.BACKEND], url_name="profile_totp_enable")
@never_cache
@login_required
def enable_totp(request):
    """
    Start turning on two-factor authentication after confirming the password. The Security section then shows
    a QR code, and the setup is finished by confirming a code from the authenticator app.

    Parameters:
        request (HttpRequest): The current request, with password in POST.

    Returns:
        HttpResponse: The Security section with the setup step. The status is 400 when the password is wrong
        or two-factor authentication is already on.
    """
    if has_totp(request.user):
        return render(
            request,
            SECURITY_SECTION_TEMPLATE,
            security_context(request, totp_enable_error="Two-factor authentication is already on."),
            status=400,
        )

    # No authenticator app exists yet, so check_reauth asks for the password only.
    auth_error = check_reauth(request.user, request.POST.get("password", ""), "")
    if auth_error:
        return render(
            request,
            SECURITY_SECTION_TEMPLATE,
            security_context(request, totp_enable_error=auth_error),
            status=400,
        )

    start_totp_setup(request.user)
    return render(request, SECURITY_SECTION_TEMPLATE, security_context(request))


@router.post("/profile/totp/confirm/", tags=[APITags.BACKEND], url_name="profile_totp_confirm")
@never_cache
@login_required
def confirm_totp(request):
    """
    Finish turning on two-factor authentication with a code from the authenticator app.

    Parameters:
        request (HttpRequest): The current request, with otp_token in POST.

    Returns:
        HttpResponse: The Security section, showing the authenticator app as on. The status is 400 when the
        code is wrong, or there is no setup in progress.
    """
    device = unconfirmed_totp_by_user(request.user)
    if device is None:
        return render(
            request,
            SECURITY_SECTION_TEMPLATE,
            security_context(request, totp_enable_error="Turn on two-factor authentication to start setup."),
            status=400,
        )

    # Strip stray spaces so a code pasted with a trailing space still works.
    token = request.POST.get("otp_token", "").strip()
    if not confirm_device(device, token):
        return render(
            request,
            SECURITY_SECTION_TEMPLATE,
            security_context(request, totp_error=INVALID_CODE_MESSAGE),
            status=400,
        )

    return render(
        request,
        SECURITY_SECTION_TEMPLATE,
        security_context(request, totp_message="Two-factor authentication is on."),
    )


@router.post("/profile/totp/cancel/", tags=[APITags.BACKEND], url_name="profile_totp_cancel")
@never_cache
@login_required
def cancel_totp(request):
    """
    Stop an unfinished two-factor setup. Nothing is turned on by this.

    Parameters:
        request (HttpRequest): The current request.

    Returns:
        HttpResponse: The Security section, with two-factor authentication still off.
    """
    clear_unconfirmed_totp(request.user)
    return render(request, SECURITY_SECTION_TEMPLATE, security_context(request))


@router.post("/profile/totp/disable/", tags=[APITags.BACKEND], url_name="profile_totp_disable")
@never_cache
@login_required
def disable_totp(request):
    """
    Turn off two-factor authentication after confirming the password and a code from the authenticator app.

    Parameters:
        request (HttpRequest): The current request, with password and otp_token in POST.

    Returns:
        HttpResponse: The Security section, showing two-factor authentication as off. The status is 400 when
        the password or code is wrong.
    """
    auth_error = check_reauth(request.user, request.POST.get("password", ""), request.POST.get("otp_token", ""))
    if auth_error:
        return render(
            request,
            SECURITY_SECTION_TEMPLATE,
            security_context(request, totp_disable_error=auth_error),
            status=400,
        )

    turn_off_totp(request.user)
    return render(
        request,
        SECURITY_SECTION_TEMPLATE,
        security_context(request, totp_message="Two-factor authentication is off."),
    )
