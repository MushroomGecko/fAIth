from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from backend.utils.authentication import enrollment_details, hash_recovery_code
from backend.utils.signup import RECOVERY_CODE_COUNT


class UsernameForm(forms.ModelForm):
    """
    The form for changing the logged-in user's username.

    A username that differs from another account's only in letter case is taken. The user's own current
    username is not checked against itself, so they can change its letter case.
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
        taken = get_user_model().objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if taken.exists():
            raise ValidationError("A user with that username already exists.")
        return username


class PasswordForm(forms.Form):
    """
    The form for setting a new password for the logged-in user.

    The current password is checked separately with check_reauth, so it is not a field here.
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
        Set the user's password to the new one and save it.

        Returns:
            User: The updated user.
        """
        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.save(update_fields=["password"])
        return self.user


def confirmed_totp_device(user):
    """
    Return the user's confirmed authenticator app device, or None if they have none.

    Parameters:
        user (User): The user to look up.

    Returns:
        TOTPDevice | None: The oldest confirmed device, if any.
    """
    return TOTPDevice.objects.filter(user=user, confirmed=True).order_by("id").first()


def unconfirmed_totp_device(user):
    """
    Return the user's unfinished authenticator app setup, or None if there isn't one.

    Parameters:
        user (User): The user to look up.

    Returns:
        TOTPDevice | None: The oldest unconfirmed device, if any.
    """
    return TOTPDevice.objects.filter(user=user, confirmed=False).order_by("id").first()


def start_totp_setup(user):
    """
    Begin turning on two-factor authentication. Any earlier unfinished setup is replaced with a new device.

    Parameters:
        user (User): The user turning on two-factor authentication.

    Returns:
        TOTPDevice: The new unconfirmed device, to be confirmed with a code from the user's app.
    """
    TOTPDevice.objects.filter(user=user, confirmed=False).delete()
    return TOTPDevice.objects.create(user=user, name="Authenticator app", confirmed=False)


def turn_off_totp(user):
    """
    Remove the user's authenticator app, so the account logs in with the password alone.

    Recovery codes are kept on the account.

    Parameters:
        user (User): The user turning off two-factor authentication.
    """
    TOTPDevice.objects.filter(user=user).delete()


def replace_recovery_codes(user):
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
    StaticDevice.objects.filter(user=user).delete()
    device = StaticDevice.objects.create(user=user, name="Recovery code", confirmed=True)
    codes = [StaticToken.random_token() for _ in range(RECOVERY_CODE_COUNT)]
    StaticToken.objects.bulk_create(
        [StaticToken(device=device, token=hash_recovery_code(code, device)) for code in codes]
    )
    return codes


def has_totp(user):
    """
    Return True if the user has a confirmed authenticator app. The settings page uses this to decide
    whether to ask for a verification code.

    Parameters:
        user (User): The user to check.

    Returns:
        bool: True if the account has a confirmed authenticator app.
    """
    return confirmed_totp_device(user) is not None


def check_reauth(user, password, otp_token):
    """
    Check the password, and the verification code if the account has an authenticator app.

    Used before sensitive actions such as changing the username or deleting the account. The code is
    derived from the account: it is only required when the user has a confirmed authenticator app.

    Parameters:
        user (User): The logged-in user performing the action.
        password (str): The password the user typed.
        otp_token (str): The verification code the user typed, or an empty string.

    Returns:
        str | None: An error message for the user, or None if the checks pass.
    """
    if not password:
        return "Enter your password to confirm."
    if not user.check_password(password):
        return "That password is not correct."

    device = confirmed_totp_device(user)
    if device is not None:
        code = (otp_token or "").strip()
        if not code:
            return "Enter the 6-digit code from your authenticator app."
        if not device.verify_token(code):
            return "That verification code is not correct."
    return None


def section_context(request, **extra):
    """
    Build the template context for the Account section. The form and has_totp are always included,
    and extra values such as error messages are added on top.

    Parameters:
        request (HttpRequest): The current request.
        **extra: Additional template values to include.

    Returns:
        dict: The context for the Account section template.
    """
    context = {"form": UsernameForm(instance=request.user), "has_totp": has_totp(request.user)}
    context.update(extra)
    return context


def security_context(request, **extra):
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
    user = request.user
    pending = unconfirmed_totp_device(user)
    context = {
        "password_form": PasswordForm(user),
        "has_totp": has_totp(user),
        "pending_totp": pending,
    }
    if pending is not None:
        context.update(enrollment_details(pending))
    context.update(extra)
    return context
