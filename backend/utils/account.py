from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django_otp.plugins.otp_totp.models import TOTPDevice


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


def confirmed_totp_device(user):
    """
    Return the user's confirmed authenticator app device, or None if they have none.

    Parameters:
        user (User): The user to look up.

    Returns:
        TOTPDevice | None: The oldest confirmed device, if any.
    """
    return TOTPDevice.objects.filter(user=user, confirmed=True).order_by("id").first()


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
