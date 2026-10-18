from asgiref.sync import sync_to_async
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from backend.utils.authentication import (
    clear_unconfirmed_totp,
    confirmed_recovery_device,
    confirmed_totp_device,
    create_recovery_codes,
    create_totp_device,
    enrollment_details,
    unconfirmed_totp_by_user,
    users_matching_username,
    verify_recovery_code,
)


class UsernameForm(forms.ModelForm):
    """
    The form for changing the logged-in user's username.

    A username that differs from another account's only in letter case is taken. The user's own current
    username is not checked against itself, so they can change its letter case.

    The form is synchronous, because Django forms are. Async callers run is_valid() and save() through sync_to_async.
    """

    class Meta:
        model = get_user_model()
        fields = ["username"]

    def clean_username(self):
        """
        Check that no other account already uses this username, ignoring letter case.

        Returns:
            str: The username, unchanged.

        Raises:
            ValidationError: If another account already uses this name in any letter case.
        """
        username = self.cleaned_data["username"]
        taken = users_matching_username(username).exclude(pk=self.instance.pk)
        if taken.exists():
            raise ValidationError("A user with that username already exists.")
        return username


class PasswordForm(forms.Form):
    """
    The form for setting a new password for the logged-in user.

    The current password is checked separately with check_reauth, so it is not a field here.

    The form is synchronous, because Django forms are. Async callers run is_valid() and save() through sync_to_async.
    """

    new_password1 = forms.CharField(
        label="New password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        """
        Parameters:
            user (User): The user whose password will change. Used for the similarity check and the current password check.
        """
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password1(self):
        """
        Check the new password against the project's password validators, and that it differs from the current one.

        Returns:
            str: The new password, unchanged.

        Raises:
            ValidationError: If the password is rejected or matches the current password.
        """
        password = self.cleaned_data["new_password1"]
        # The password is not saved yet, so check_password still compares against the current password.
        if self.user.check_password(password):
            raise ValidationError("Choose a password that is different from your current one.")
        validate_password(password, self.user)
        return password

    def clean(self):
        """
        Check that the two new passwords match.

        Returns:
            dict: The cleaned data.
        """
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")
        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", "The two passwords do not match.")
        return cleaned_data

    def save(self):
        """
        Set the user's password to the new one and save it. Synchronous, so async callers use sync_to_async.

        Returns:
            User: The updated user.
        """
        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.save(update_fields=["password"])
        return self.user


async def start_totp_setup(user):
    """
    Begin turning on two-factor authentication. Any earlier unfinished setup is replaced with a new device.

    Parameters:
        user (User): The user turning on two-factor authentication.

    Returns:
        TOTPDevice: The new unconfirmed device, to be confirmed with a code from the user's app.
    """
    await clear_unconfirmed_totp(user)
    return await create_totp_device(user)


async def turn_off_totp(user):
    """
    Remove the user's authenticator app, so the account logs in with the password alone.

    Recovery codes are kept on the account.

    Parameters:
        user (User): The user turning off two-factor authentication.
    """
    await TOTPDevice.objects.filter(user=user).adelete()


async def replace_recovery_codes(user):
    """
    Replace the user's recovery codes with a new set. The old codes stop working straight away.

    The new codes are saved as soon as this runs, so they work even if the user never clicks through
    the page afterward. Only hashes are stored, so the plain-text codes returned here are shown once.

    Parameters:
        user (User): The user whose recovery codes are replaced.

    Returns:
        list[str]: The new plain-text recovery codes, to show the user one time.
    """
    # Deleting the recovery-code device also deletes its tokens, so the old codes can't be used.
    await StaticDevice.objects.filter(user=user).adelete()
    return await create_recovery_codes(user, confirmed=True)


async def has_totp(user):
    """
    Return True if the user has a confirmed authenticator app. The settings page uses this to decide
    whether to ask for a verification code.

    Parameters:
        user (User): The user to check.

    Returns:
        bool: True if the account has a confirmed authenticator app.
    """
    return await confirmed_totp_device(user) is not None


async def check_reauth(request, user, allow_recovery_code=False):
    """
    Check that the user is who they say they are before a sensitive action such as changing the username
    or deleting the account.

    The password and authenticator code are read from request.POST. Without a recovery code, the password is
    required, and so is the verification code when the account has a confirmed authenticator app. When
    allow_recovery_code is True, a recovery code on its own is also accepted in place of both the password and
    the authenticator code. The two options are: (password and authenticator code) or (recovery code). Giving
    both codes is an error, and the check runs before any code is verified, so entering both never uses up a
    recovery code.

    Parameters:
        request (HttpRequest): The current request, with password, otp_token, and recovery_code in POST.
        user (User): The logged-in user performing the action.
        allow_recovery_code (bool): Whether this action accepts a recovery code. Only the actions that show a
            recovery code field pass True. Defaults to False.

    Returns:
        str | None: An error message for the user, or None if the checks pass.
    """
    password = request.POST.get("password", "")
    code = request.POST.get("otp_token", "").strip()
    recovery = request.POST.get("recovery_code", "").strip() if allow_recovery_code else ""

    if code and recovery:
        # Checked before anything is verified, so a recovery code isn't used up when both are entered.
        return "Enter either an authenticator code or a recovery code, not both."

    if recovery:
        recovery_device = await confirmed_recovery_device(user)
        if recovery_device is None or not await verify_recovery_code(recovery_device, recovery):
            return "That recovery code is not correct."
        return None

    if not password:
        return "Enter your password to confirm."
    if not await user.acheck_password(password):
        return "That password is not correct."

    device = await confirmed_totp_device(user)
    if device is None:
        return None

    if not code:
        if allow_recovery_code:
            return (
                "Enter the 6-digit code from your authenticator app, or use a recovery code instead of your password."
            )
        return "Enter the 6-digit code from your authenticator app."
    # verify_token saves throttling state to the database, so it runs in a thread.
    if not await sync_to_async(device.verify_token, thread_sensitive=True)(code):
        return "That verification code is not correct."
    return None


async def section_context(request, **extra):
    """
    Build the template context for the Account section. The form and has_totp are always included,
    and extra values such as error messages are added on top.

    Parameters:
        request (HttpRequest): The current request.
        **extra: Additional template values to include.

    Returns:
        dict: The context for the Account section template.
    """
    # request.user is a lazy wrapper that queries the database synchronously, so use the async accessor.
    user = await request.auser()
    context = {"form": UsernameForm(instance=user), "has_totp": await has_totp(user)}
    context.update(extra)
    return context


async def security_context(request, **extra):
    """
    Build the template context for the Security section. The password form, has_totp, and any unfinished
    two-factor setup are always included, and extra values such as error messages are added on top.

    When a setup is unfinished, its QR code and secret are included so the page can show them again.

    Parameters:
        request (HttpRequest): The current request.
        **extra: Additional template values to include.

    Returns:
        dict: The context for the Security section template.
    """
    # request.user is a lazy wrapper that queries the database synchronously, so use the async accessor.
    user = await request.auser()
    pending = await unconfirmed_totp_by_user(user)
    context = {
        "password_form": PasswordForm(user),
        "has_totp": await has_totp(user),
        "pending_totp": pending,
    }
    if pending is not None:
        context.update(await enrollment_details(pending))
    context.update(extra)
    return context
