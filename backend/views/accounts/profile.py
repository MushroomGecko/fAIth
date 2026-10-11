from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from ninja import Router

from backend.utils.account import UsernameForm, check_reauth, has_totp
from fAIth.api_tags import APITags

# Create router for account endpoints
router = Router()

# The Account section partial, and the greeting that the username change swaps into the navbar.
ACCOUNT_SECTION_TEMPLATE = "profile/partials/settings.html"
GREETING_TEMPLATE = "profile/partials/greeting.html"


def section_context(request, **extra):
    """
    Build the template context for the Account section. The form and has_totp are always included,
    and extra values such as error messages are added on top.

    Parameters:
        request (HttpRequest): The current request.
        **extra: Additional template values to include.

    Returns:
        dict: The context for ACCOUNT_SECTION_TEMPLATE.
    """
    context = {"form": UsernameForm(instance=request.user), "has_totp": has_totp(request.user)}
    context.update(extra)
    return context


@router.get("/profile/", tags=[APITags.BACKEND], url_name="profile")
@login_required
def account_page(request):
    """
    Show the profile page. Anonymous users are redirected to the login page.
    """
    return render(request, "profile/index.html")


@router.get("/profile/account/", tags=[APITags.BACKEND], url_name="profile_account")
@login_required
def account_section(request):
    """
    Show the Account section with the username form and the danger zone.
    """
    return render(request, ACCOUNT_SECTION_TEMPLATE, section_context(request))


@router.post("/profile/username/", tags=[APITags.BACKEND], url_name="profile_username")
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
@login_required
def security_section(request):
    """
    Show the Security section. Nothing is in it yet.
    """
    return render(request, "profile/partials/security.html")
