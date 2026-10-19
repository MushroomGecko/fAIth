"""Tests for the profile endpoints in backend.views.accounts.profile."""

from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from backend.utils.authentication import (
    RECOVERY_DEVICE_NAME,
    TOTP_DEVICE_NAME,
    create_recovery_codes,
    hash_recovery_code,
)

User = get_user_model()
PASSWORD = "a-long-test-password-123"
NEW_PASSWORD = "another-long-password-456"
# The error shown when a recovery code is sent with a password or an authenticator code.
COMBINATION_ERROR = "Enter either your password and an authenticator code, or a recovery code on its own, not both."


def _totp_code(device):
    """Return the 6-digit code the authenticator app would show for this device right now."""
    return str(TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift).token()).zfill(device.digits)


class ProfileViewTestBase(TestCase):
    """Shared setup: a logged-in user with a recovery code set."""

    def setUp(self):
        self.user = User.objects.create_user(username="profile-user", password=PASSWORD)
        self.client.force_login(self.user)
        self.codes = async_to_sync(create_recovery_codes)(self.user, confirmed=True)
        self.recovery_device = StaticDevice.objects.get(user=self.user, name=RECOVERY_DEVICE_NAME)

    def _post(self, url_name, **data):
        """POST to a profile endpoint by its URL name."""
        return self.client.post(reverse(url_name), data)

    def _get(self, url_name):
        """GET a profile endpoint by its URL name."""
        return self.client.get(reverse(url_name))

    def _add_confirmed_totp(self):
        """Turn on an authenticator app for the user and return it."""
        return TOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=True)

    def _code_still_works(self, code):
        """Return True if this recovery code's token still exists on the original device."""
        token_hash = async_to_sync(hash_recovery_code)(code, self.recovery_device)
        return StaticToken.objects.filter(device_id=self.recovery_device.pk, token=token_hash).exists()

    def _password_works(self, password):
        """Return True if the stored password matches."""
        self.user.refresh_from_db()
        return self.user.check_password(password)


class TestLoginRequired(TestCase):
    """Every profile endpoint sends anonymous visitors to the login page."""

    ROUTES = [
        ("GET", "api:profile"),
        ("GET", "api:profile_account"),
        ("POST", "api:profile_username"),
        ("POST", "api:profile_delete"),
        ("GET", "api:profile_security"),
        ("POST", "api:profile_password"),
        ("POST", "api:profile_recovery_codes"),
        ("POST", "api:profile_totp_enable"),
        ("POST", "api:profile_totp_confirm"),
        ("POST", "api:profile_totp_cancel"),
        ("POST", "api:profile_totp_disable"),
    ]

    def test_anonymous_requests_redirect_to_login(self):
        """Each endpoint redirects an anonymous visitor to the login page, without changing anything."""
        for method, url_name in self.ROUTES:
            with self.subTest(route=url_name):
                response = getattr(self.client, method.lower())(reverse(url_name))

                assert response.status_code == 302
                assert response.url.startswith(settings.LOGIN_URL)


class TestProfilePage(ProfileViewTestBase):
    """Tests for GET /profile/."""

    def test_shows_profile_template(self):
        """The profile page renders for a logged-in user."""
        response = self._get("api:profile")

        assert response.status_code == 200
        self.assertTemplateUsed(response, "profile/index.html")

    def test_is_never_cached(self):
        """The profile page is marked no-store."""
        response = self._get("api:profile")

        assert "no-store" in response["Cache-Control"]

    def test_opening_profile_clears_unfinished_setup(self):
        """Opening the profile drops any unfinished authenticator setup."""
        TOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=False)

        self._get("api:profile")

        assert not TOTPDevice.objects.filter(user=self.user, confirmed=False).exists()

    def test_opening_profile_keeps_confirmed_authenticator(self):
        """A confirmed authenticator survives opening the profile."""
        device = self._add_confirmed_totp()

        self._get("api:profile")

        assert TOTPDevice.objects.filter(pk=device.pk).exists()


class TestAccountSection(ProfileViewTestBase):
    """Tests for GET /profile/account/."""

    def test_shows_account_template(self):
        """The Account section renders its partial template."""
        response = self._get("api:profile_account")

        assert response.status_code == 200
        self.assertTemplateUsed(response, "profile/partials/settings.html")

    def test_has_totp_reflects_authenticator_state(self):
        """The section reports whether the authenticator app is on."""
        assert self._get("api:profile_account").context["has_totp"] is False

        self._add_confirmed_totp()

        assert self._get("api:profile_account").context["has_totp"] is True

    def test_opening_section_clears_unfinished_setup(self):
        """Clicking Account drops any unfinished authenticator setup."""
        TOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=False)

        self._get("api:profile_account")

        assert not TOTPDevice.objects.filter(user=self.user, confirmed=False).exists()


class TestChangeUsername(ProfileViewTestBase):
    """Tests for POST /profile/username/."""

    def test_correct_password_changes_username(self):
        """With the right password, the username changes."""
        response = self._post("api:profile_username", username="renamed-user", password=PASSWORD)

        assert response.status_code == 200
        self.user.refresh_from_db()
        assert self.user.username == "renamed-user"

    def test_wrong_password_keeps_username_and_shows_error(self):
        """A wrong password refuses the change, returns status 400, and shows the password error."""
        response = self._post("api:profile_username", username="renamed-user", password="wrong-password-123")

        assert response.status_code == 400
        assert response.context["username_auth_error"] == "That password is not correct."
        self.user.refresh_from_db()
        assert self.user.username == "profile-user"

    def test_wrong_password_does_not_reveal_taken_name(self):
        """With a taken name and a wrong password, the page doesn't reveal that the name is taken."""
        User.objects.create_user(username="taken-name", password=PASSWORD)

        response = self._post("api:profile_username", username="taken-name", password="wrong-password-123")

        assert response.context["username_auth_error"] == "That password is not correct."
        assert b"A user with that username already exists." not in response.content

    def test_taken_name_is_rejected(self):
        """A name another account uses is refused with status 400."""
        User.objects.create_user(username="taken-name", password=PASSWORD)

        response = self._post("api:profile_username", username="taken-name", password=PASSWORD)

        assert response.status_code == 400
        assert "A user with that username already exists." in response.context["form"].errors["username"]
        self.user.refresh_from_db()
        assert self.user.username == "profile-user"

    def test_taken_name_in_other_case_is_rejected(self):
        """A name that differs from another account's only in case is refused."""
        User.objects.create_user(username="Taken-Name", password=PASSWORD)

        response = self._post("api:profile_username", username="taken-name", password=PASSWORD)

        assert response.status_code == 400

    def test_can_change_own_name_case(self):
        """The user can change the letter case of their own username."""
        response = self._post("api:profile_username", username="PROFILE-USER", password=PASSWORD)

        assert response.status_code == 200
        self.user.refresh_from_db()
        assert self.user.username == "PROFILE-USER"

    def test_authenticator_account_refuses_bad_combinations(self):
        """With an authenticator on, only the right password plus a valid code changes the username."""
        device = self._add_confirmed_totp()
        code = _totp_code(device)
        cases = [
            ("password alone", {"password": PASSWORD}, "Enter the 6-digit code from your authenticator app."),
            ("code alone", {"otp_token": code}, "Enter your password to confirm."),
            (
                "wrong password, good code",
                {"password": "wrong-password-123", "otp_token": code},
                "That password is not correct.",
            ),
            (
                "good password, wrong code",
                {"password": PASSWORD, "otp_token": "000000"},
                "That verification code is not correct.",
            ),
            (
                "wrong password, wrong code",
                {"password": "wrong-password-123", "otp_token": "000000"},
                "That password is not correct.",
            ),
        ]
        for name, data, error in cases:
            with self.subTest(case=name):
                response = self._post("api:profile_username", username="renamed-user", **data)

                assert response.status_code == 400
                assert response.context["username_auth_error"] == error
                self.user.refresh_from_db()
                assert self.user.username == "profile-user"

    def test_authenticator_account_with_correct_code_changes_username(self):
        """With the right password and code, the username changes."""
        device = self._add_confirmed_totp()

        response = self._post(
            "api:profile_username",
            username="renamed-user",
            password=PASSWORD,
            otp_token=_totp_code(device),
        )

        assert response.status_code == 200
        self.user.refresh_from_db()
        assert self.user.username == "renamed-user"

    def test_recovery_code_is_not_accepted_for_username_change(self):
        """A recovery code can't replace the password for a username change."""
        response = self._post(
            "api:profile_username",
            username="renamed-user",
            recovery_code=self.codes[0],
        )

        assert response.status_code == 400
        self.user.refresh_from_db()
        assert self.user.username == "profile-user"
        assert self._code_still_works(self.codes[0]) is True


class TestDeleteAccount(ProfileViewTestBase):
    """Tests for POST /profile/delete/."""

    def test_success_deletes_account_and_redirects(self):
        """With the right password, the account is deleted and HTMX is sent to the main site."""
        response = self._post("api:profile_delete", password=PASSWORD)

        assert response.status_code == 200
        assert response["HX-Redirect"] == settings.LOGOUT_REDIRECT_URL
        assert not User.objects.filter(username="profile-user").exists()

    def test_success_logs_out(self):
        """Deleting the account signs the browser out."""
        self._post("api:profile_delete", password=PASSWORD)

        assert "_auth_user_id" not in self.client.session

    def test_wrong_password_keeps_account(self):
        """A wrong password returns status 400 and keeps the account."""
        response = self._post("api:profile_delete", password="wrong-password-123")

        assert response.status_code == 400
        assert User.objects.filter(username="profile-user").exists()
        assert response.context["delete_auth_error"] == "That password is not correct."

    def test_authenticator_account_refuses_bad_combinations(self):
        """With an authenticator on, only the right password plus a valid code deletes the account."""
        device = self._add_confirmed_totp()
        code = _totp_code(device)
        cases = [
            ("password alone", {"password": PASSWORD}, "Enter the 6-digit code from your authenticator app."),
            ("code alone", {"otp_token": code}, "Enter your password to confirm."),
            (
                "wrong password, good code",
                {"password": "wrong-password-123", "otp_token": code},
                "That password is not correct.",
            ),
            (
                "good password, wrong code",
                {"password": PASSWORD, "otp_token": "000000"},
                "That verification code is not correct.",
            ),
            (
                "wrong password, wrong code",
                {"password": "wrong-password-123", "otp_token": "000000"},
                "That password is not correct.",
            ),
        ]
        for name, data, error in cases:
            with self.subTest(case=name):
                response = self._post("api:profile_delete", **data)

                assert response.status_code == 400
                assert response.context["delete_auth_error"] == error
                assert User.objects.filter(username="profile-user").exists()

    def test_recovery_code_alone_is_refused(self):
        """Deleting the account needs the password, so a recovery code alone is refused."""
        response = self._post("api:profile_delete", recovery_code=self.codes[0])

        assert response.status_code == 400
        assert User.objects.filter(username="profile-user").exists()

    def test_authenticator_account_with_correct_code_deletes(self):
        """With the right password and code, the account is deleted."""
        device = self._add_confirmed_totp()

        self._post("api:profile_delete", password=PASSWORD, otp_token=_totp_code(device))

        assert not User.objects.filter(username="profile-user").exists()


class TestSecuritySection(ProfileViewTestBase):
    """Tests for GET /profile/security/."""

    def test_shows_security_template_with_unbound_password_form(self):
        """The Security section renders with an empty password form."""
        response = self._get("api:profile_security")

        assert response.status_code == 200
        self.assertTemplateUsed(response, "profile/partials/security.html")
        assert response.context["password_form"].is_bound is False

    def test_reports_authenticator_state(self):
        """The section reports whether the authenticator app is on."""
        assert self._get("api:profile_security").context["has_totp"] is False

        self._add_confirmed_totp()

        assert self._get("api:profile_security").context["has_totp"] is True

    def test_shows_pending_setup_qr_when_unfinished(self):
        """An unfinished setup is shown again with its QR code and secret."""
        pending = TOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=False)

        response = self._get("api:profile_security")

        assert response.context["pending_totp"].pk == pending.pk
        assert "<svg" in response.context["svg"]


class TestChangePassword(ProfileViewTestBase):
    """Tests for POST /profile/password/."""

    def test_correct_password_changes_password_and_keeps_browser_signed_in(self):
        """With the current password and matching new passwords, the password changes and this browser stays signed in."""
        response = self._post(
            "api:profile_password",
            password=PASSWORD,
            new_password1=NEW_PASSWORD,
            new_password2=NEW_PASSWORD,
        )

        assert response.status_code == 200
        assert response.context["password_saved"] is True
        assert self._password_works(NEW_PASSWORD)
        assert not self._password_works(PASSWORD)
        assert "_auth_user_id" in self.client.session
        assert self._get("api:profile_security").status_code == 200

    def test_wrong_current_password_is_refused(self):
        """A wrong current password returns status 400 and leaves the password alone."""
        response = self._post(
            "api:profile_password",
            password="wrong-password-123",
            new_password1=NEW_PASSWORD,
            new_password2=NEW_PASSWORD,
        )

        assert response.status_code == 400
        assert response.context["password_auth_error"] == "That password is not correct."
        assert self._password_works(PASSWORD)

    def test_mismatched_new_passwords_are_refused(self):
        """Two different new passwords return status 400 and change nothing."""
        response = self._post(
            "api:profile_password",
            password=PASSWORD,
            new_password1=NEW_PASSWORD,
            new_password2="different-pass-789",
        )

        assert response.status_code == 400
        assert "new_password2" in response.context["password_form"].errors
        assert self._password_works(PASSWORD)

    def test_reusing_current_password_is_refused(self):
        """The new password can't be the current one."""
        response = self._post(
            "api:profile_password",
            password=PASSWORD,
            new_password1=PASSWORD,
            new_password2=PASSWORD,
        )

        assert response.status_code == 400
        assert "new_password1" in response.context["password_form"].errors

    def test_recovery_code_can_replace_current_password(self):
        """A recovery code on its own is accepted in place of the current password, and is used up."""
        response = self._post(
            "api:profile_password",
            recovery_code=self.codes[0],
            new_password1=NEW_PASSWORD,
            new_password2=NEW_PASSWORD,
        )

        assert response.status_code == 200
        assert self._password_works(NEW_PASSWORD)
        assert self._code_still_works(self.codes[0]) is False

    def test_recovery_code_combined_with_another_factor_is_refused(self):
        """A recovery code sent with the password or an authenticator code is refused, and the code is kept."""
        device = self._add_confirmed_totp()
        cases = [
            ("password and recovery code", {"password": PASSWORD}),
            ("authenticator code and recovery code", {"otp_token": _totp_code(device)}),
        ]
        for name, data in cases:
            with self.subTest(case=name):
                response = self._post(
                    "api:profile_password",
                    recovery_code=self.codes[0],
                    new_password1=NEW_PASSWORD,
                    new_password2=NEW_PASSWORD,
                    **data,
                )

                assert response.status_code == 400
                assert response.context["password_auth_error"] == COMBINATION_ERROR
                assert self._password_works(PASSWORD)
                assert self._code_still_works(self.codes[0]) is True

    def test_authenticator_account_refuses_bad_combinations(self):
        """With an authenticator on, only the right password plus a valid code changes the password."""
        device = self._add_confirmed_totp()
        code = _totp_code(device)
        cases = [
            (
                "password alone",
                {"password": PASSWORD},
                "Enter the 6-digit code from your authenticator app, or use a recovery code instead of your password.",
            ),
            ("code alone", {"otp_token": code}, "Enter your password to confirm."),
            (
                "wrong password, good code",
                {"password": "wrong-password-123", "otp_token": code},
                "That password is not correct.",
            ),
            (
                "good password, wrong code",
                {"password": PASSWORD, "otp_token": "000000"},
                "That verification code is not correct.",
            ),
            (
                "wrong password, wrong code",
                {"password": "wrong-password-123", "otp_token": "000000"},
                "That password is not correct.",
            ),
        ]
        for name, data, error in cases:
            with self.subTest(case=name):
                response = self._post(
                    "api:profile_password",
                    new_password1=NEW_PASSWORD,
                    new_password2=NEW_PASSWORD,
                    **data,
                )

                assert response.status_code == 400
                assert response.context["password_auth_error"] == error
                assert self._password_works(PASSWORD)


class TestRefreshRecoveryCodes(ProfileViewTestBase):
    """Tests for POST /profile/recovery-codes/."""

    def test_correct_password_issues_ten_new_codes_once(self):
        """With the right password, ten new codes are shown in a no-store response."""
        response = self._post("api:profile_recovery_codes", password=PASSWORD)

        assert response.status_code == 200
        assert len(response.context["recovery_codes"]) == 10
        assert set(response.context["recovery_codes"]).isdisjoint(self.codes)
        assert "no-store" in response["Cache-Control"]

    def test_new_codes_replace_old_ones(self):
        """The old codes stop working, and the new recovery device is confirmed and replaces the old one."""
        self._post("api:profile_recovery_codes", password=PASSWORD)

        assert self._code_still_works(self.codes[0]) is False
        assert not StaticDevice.objects.filter(pk=self.recovery_device.pk).exists()
        assert StaticDevice.objects.filter(user=self.user, name=RECOVERY_DEVICE_NAME, confirmed=True).count() == 1

    def test_wrong_password_keeps_old_codes(self):
        """A wrong password returns status 400 and keeps the existing codes."""
        response = self._post("api:profile_recovery_codes", password="wrong-password-123")

        assert response.status_code == 400
        assert self._code_still_works(self.codes[0]) is True

    def test_authenticator_account_refuses_bad_combinations(self):
        """With an authenticator on, only the right password plus a valid code replaces the codes."""
        device = self._add_confirmed_totp()
        code = _totp_code(device)
        cases = [
            ("password alone", {"password": PASSWORD}, "Enter the 6-digit code from your authenticator app."),
            ("code alone", {"otp_token": code}, "Enter your password to confirm."),
            (
                "wrong password, good code",
                {"password": "wrong-password-123", "otp_token": code},
                "That password is not correct.",
            ),
            (
                "good password, wrong code",
                {"password": PASSWORD, "otp_token": "000000"},
                "That verification code is not correct.",
            ),
            (
                "wrong password, wrong code",
                {"password": "wrong-password-123", "otp_token": "000000"},
                "That password is not correct.",
            ),
        ]
        for name, data, error in cases:
            with self.subTest(case=name):
                response = self._post("api:profile_recovery_codes", **data)

                assert response.status_code == 400
                assert response.context["recovery_auth_error"] == error
                assert self._code_still_works(self.codes[0]) is True


class TestEnableTotp(ProfileViewTestBase):
    """Tests for POST /profile/totp/enable/."""

    def test_correct_password_starts_setup_without_turning_it_on(self):
        """With the right password, an unconfirmed authenticator is created, the QR code is shown, and the app stays off."""
        response = self._post("api:profile_totp_enable", password=PASSWORD)

        assert response.status_code == 200
        assert TOTPDevice.objects.filter(user=self.user, confirmed=False).exists()
        assert not TOTPDevice.objects.filter(user=self.user, confirmed=True).exists()
        assert "<svg" in response.context["svg"]

    def test_wrong_password_creates_no_setup(self):
        """A wrong password returns status 400 and creates nothing."""
        response = self._post("api:profile_totp_enable", password="wrong-password-123")

        assert response.status_code == 400
        assert not TOTPDevice.objects.filter(user=self.user).exists()
        assert response.context["totp_enable_error"] == "That password is not correct."

    def test_already_on_is_refused(self):
        """Turning on an authenticator that is already on is refused."""
        self._add_confirmed_totp()

        response = self._post("api:profile_totp_enable", password=PASSWORD)

        assert response.status_code == 400
        assert response.context["totp_enable_error"] == "Two-factor authentication is already on."
        assert not TOTPDevice.objects.filter(user=self.user, confirmed=False).exists()

    def test_new_setup_replaces_earlier_unfinished_setup(self):
        """Starting again leaves only one unfinished setup."""
        self._post("api:profile_totp_enable", password=PASSWORD)
        self._post("api:profile_totp_enable", password=PASSWORD)

        assert TOTPDevice.objects.filter(user=self.user, confirmed=False).count() == 1


class TestConfirmTotp(ProfileViewTestBase):
    """Tests for POST /profile/totp/confirm/."""

    def setUp(self):
        super().setUp()
        self._post("api:profile_totp_enable", password=PASSWORD)
        self.pending = TOTPDevice.objects.get(user=self.user, confirmed=False)

    def test_correct_code_turns_on_authenticator(self):
        """A correct code confirms the setup and shows the app as on."""
        response = self._post("api:profile_totp_confirm", otp_token=_totp_code(self.pending))

        assert response.status_code == 200
        assert response.context["totp_message"] == "Two-factor authentication is on."
        self.pending.refresh_from_db()
        assert self.pending.confirmed is True

    def test_code_with_surrounding_spaces_is_accepted(self):
        """A code pasted with extra spaces still turns the app on."""
        self._post("api:profile_totp_confirm", otp_token=f" {_totp_code(self.pending)} ")

        self.pending.refresh_from_db()
        assert self.pending.confirmed is True

    def test_wrong_code_keeps_setup_pending(self):
        """A wrong code returns status 400 and leaves the setup unconfirmed."""
        response = self._post("api:profile_totp_confirm", otp_token="000000")

        assert response.status_code == 400
        assert response.context["totp_error"]
        self.pending.refresh_from_db()
        assert self.pending.confirmed is False

    def test_no_setup_in_progress_is_refused(self):
        """Confirming with no unfinished setup returns status 400."""
        self._post("api:profile_totp_cancel")

        response = self._post("api:profile_totp_confirm", otp_token=_totp_code(self.pending))

        assert response.status_code == 400
        assert response.context["totp_enable_error"] == "Turn on two-factor authentication to start setup."


class TestCancelTotp(ProfileViewTestBase):
    """Tests for POST /profile/totp/cancel/."""

    def test_removes_unfinished_setup(self):
        """Cancelling deletes the unfinished setup."""
        self._post("api:profile_totp_enable", password=PASSWORD)

        response = self._post("api:profile_totp_cancel")

        assert response.status_code == 200
        assert not TOTPDevice.objects.filter(user=self.user, confirmed=False).exists()

    def test_keeps_confirmed_authenticator(self):
        """Cancelling never removes an authenticator that is on."""
        device = self._add_confirmed_totp()
        self._post("api:profile_totp_enable", password=PASSWORD)

        self._post("api:profile_totp_cancel")

        assert TOTPDevice.objects.filter(pk=device.pk, confirmed=True).exists()


class TestDisableTotp(ProfileViewTestBase):
    """Tests for POST /profile/totp/disable/."""

    def test_authenticator_account_refuses_bad_combinations(self):
        """With an authenticator on, only the right password plus a valid code turns it off."""
        device = self._add_confirmed_totp()
        code = _totp_code(device)
        cases = [
            (
                "password alone",
                {"password": PASSWORD},
                "Enter the 6-digit code from your authenticator app, or use a recovery code instead of your password.",
            ),
            ("code alone", {"otp_token": code}, "Enter your password to confirm."),
            (
                "wrong password, good code",
                {"password": "wrong-password-123", "otp_token": code},
                "That password is not correct.",
            ),
            (
                "good password, wrong code",
                {"password": PASSWORD, "otp_token": "000000"},
                "That verification code is not correct.",
            ),
            (
                "wrong password, wrong code",
                {"password": "wrong-password-123", "otp_token": "000000"},
                "That password is not correct.",
            ),
        ]
        for name, data, error in cases:
            with self.subTest(case=name):
                response = self._post("api:profile_totp_disable", **data)

                assert response.status_code == 400
                assert response.context["totp_disable_error"] == error
                assert TOTPDevice.objects.filter(pk=device.pk).exists()

    def test_password_and_code_turn_off_authenticator(self):
        """The right password and a valid code turn the authenticator off."""
        device = self._add_confirmed_totp()

        response = self._post("api:profile_totp_disable", password=PASSWORD, otp_token=_totp_code(device))

        assert response.status_code == 200
        assert response.context["totp_message"] == "Two-factor authentication is off."
        assert not TOTPDevice.objects.filter(pk=device.pk).exists()

    def test_recovery_code_alone_turns_off_authenticator(self):
        """A recovery code on its own turns the authenticator off, and the code is used up."""
        device = self._add_confirmed_totp()

        response = self._post("api:profile_totp_disable", recovery_code=self.codes[0])

        assert response.status_code == 200
        assert not TOTPDevice.objects.filter(pk=device.pk).exists()
        assert self._code_still_works(self.codes[0]) is False

    def test_recovery_code_combined_with_another_factor_is_refused(self):
        """A recovery code sent with the password or an authenticator code is refused, and the code is kept."""
        device = self._add_confirmed_totp()
        cases = [
            ("password and recovery code", {"password": PASSWORD}),
            ("authenticator code and recovery code", {"otp_token": _totp_code(device)}),
        ]
        for name, data in cases:
            with self.subTest(case=name):
                response = self._post("api:profile_totp_disable", recovery_code=self.codes[0], **data)

                assert response.status_code == 400
                assert response.context["totp_disable_error"] == COMBINATION_ERROR
                assert TOTPDevice.objects.filter(pk=device.pk).exists()
                assert self._code_still_works(self.codes[0]) is True
