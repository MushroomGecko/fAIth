"""Tests for the signup endpoints in backend.views.accounts.signup."""

from unittest.mock import AsyncMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice

from backend.models import EncryptedTOTPDevice
from backend.utils.authentication import INVALID_CODE_MESSAGE, RECOVERY_DEVICE_NAME, TOTP_DEVICE_NAME
from backend.utils.hashing import username_hmac
from backend.utils.signup import (
    ENROLLMENT_STEP,
    PENDING_CODES_SESSION_KEY,
    PENDING_DEVICE_SESSION_KEY,
    SKIP_STEP,
)

User = get_user_model()
PASSWORD = "a-long-test-password-123"


def _totp_code(device):
    """Return the 6-digit code the authenticator app would show for this device right now."""
    return str(TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift).token()).zfill(device.digits)


def _signup_data(username="new-signup-user", password1=PASSWORD, password2=PASSWORD, **extra):
    """Build the POST data for creating an account."""
    data = {"username": username, "password1": password1, "password2": password2}
    data.update(extra)
    return data


class SignupViewTestBase(TestCase):
    """Shared helpers for the signup view tests."""

    def setUp(self):
        self.url = reverse("api:signup")

    def _post(self, **data):
        """POST to the signup endpoint with the given form values."""
        return self.client.post(self.url, data)

    def _create_account(self, username="new-signup-user"):
        """Create an account through the signup form and return the response."""
        return self.client.post(self.url, _signup_data(username=username))

    def _pending_totp(self, username="new-signup-user"):
        """Return the unconfirmed authenticator device created for this signup."""
        return EncryptedTOTPDevice.objects.get(user__username=username, confirmed=False)


# (name, next value sent, next value the page should keep)
SIGNUP_NEXT_CASES = [
    ("local next", "/books/", "/books/"),
    ("external next", "https://evil.example.com/", ""),
    ("protocol-relative next", "//evil.example.com/", ""),
    ("javascript next", "javascript:alert(1)", ""),
    ("no next", "", ""),
]

# (name, next value sent, query string the redirect to login should end with)
SIGNUP_REDIRECT_CASES = [
    ("local next", "/books/", "?next=%2Fbooks%2F"),
    ("external next", "https://evil.example.com/", ""),
    ("protocol-relative next", "//evil.example.com/", ""),
    ("javascript next", "javascript:alert(1)", ""),
    ("no next", "", ""),
]


class TestSignupKeepsNext(SignupViewTestBase):
    """The "next" page from the login link is carried through the signup steps and back to login."""

    def test_signup_page_keeps_only_local_next(self):
        """The signup page passes on a local next value in a hidden field. Anything else is dropped."""
        for name, sent, kept in SIGNUP_NEXT_CASES:
            with self.subTest(case=name):
                response = self.client.get(self.url, {"next": sent})

                assert response.context["next"] == kept
                assert f'name="next" value="{kept}"' in response.content.decode()
                if kept:
                    assert f'action="{self.url}?next={kept}"' in response.content.decode()
                else:
                    assert f'action="{self.url}"' in response.content.decode()

    def test_invalid_signup_form_keeps_only_local_next(self):
        """A rejected signup shows the form again with the same next rules applied."""
        for name, sent, kept in SIGNUP_NEXT_CASES:
            with self.subTest(case=name):
                response = self.client.post(self.url, {**_signup_data(password2="does-not-match-123"), "next": sent})

                assert response.status_code == 400
                assert response.context["next"] == kept

    def test_setup_step_keeps_only_local_next_after_wrong_code(self):
        """A wrong code shows the setup step again with the same next rules applied."""
        for index, (name, sent, kept) in enumerate(SIGNUP_NEXT_CASES):
            with self.subTest(case=name):
                self._create_account(username=f"next-wrong-{index}")

                response = self._post(step=ENROLLMENT_STEP, otp_token="000000", next=sent)

                assert response.status_code == 400
                assert response.context["next"] == kept

    def test_confirm_redirects_to_login_with_only_local_next(self):
        """After the authenticator is confirmed, login gets the page to return to, if it is local."""
        login_url = reverse("api:login")
        for index, (name, sent, suffix) in enumerate(SIGNUP_REDIRECT_CASES):
            with self.subTest(case=name):
                username = f"next-confirm-{index}"
                self._create_account(username=username)

                response = self._post(
                    step=ENROLLMENT_STEP,
                    otp_token=_totp_code(self._pending_totp(username)),
                    next=sent,
                )

                assert response.status_code == 302
                assert response.url == f"{login_url}{suffix}"

    def test_skip_redirects_to_login_with_only_local_next(self):
        """Skipping the authenticator sends the user to login, with the page to return to if it is local."""
        login_url = reverse("api:login")
        for index, (name, sent, suffix) in enumerate(SIGNUP_REDIRECT_CASES):
            with self.subTest(case=name):
                self._create_account(username=f"next-skip-{index}")

                response = self._post(step=SKIP_STEP, next=sent)

                assert response.status_code == 302
                assert response.url == f"{login_url}{suffix}"


class TestSignupPage(SignupViewTestBase):
    """Tests for GET /signup/."""

    def test_shows_signup_template_with_unbound_form(self):
        """The signup page renders the signup template with an empty, unbound form."""
        response = self.client.get(self.url)

        assert response.status_code == 200
        self.assertTemplateUsed(response, "registration/signup.html")
        assert response.context["form"].is_bound is False

    def test_is_never_cached(self):
        """The signup page is marked no-store, so the browser doesn't keep it."""
        response = self.client.get(self.url)

        assert "no-store" in response["Cache-Control"]

    def test_abandons_unfinished_setup_but_keeps_account_and_recovery_codes(self):
        """Opening a fresh signup page drops the unfinished authenticator setup, keeps the account and its
        recovery codes, and clears the pending enrollment from the session."""
        self._create_account()
        assert self._pending_totp()

        self.client.get(self.url)

        assert not EncryptedTOTPDevice.objects.filter(user__username="new-signup-user", confirmed=False).exists()
        assert User.objects.filter(username=username_hmac("new-signup-user")).exists()
        assert StaticDevice.objects.filter(user__username="new-signup-user", name=RECOVERY_DEVICE_NAME).exists()
        assert PENDING_DEVICE_SESSION_KEY not in self.client.session
        assert PENDING_CODES_SESSION_KEY not in self.client.session


class TestCreateAccount(SignupViewTestBase):
    """Tests for POST /signup/ when creating a new account."""

    def test_valid_form_shows_authenticator_step(self):
        """A valid form creates the account and shows the authenticator setup page with status 200."""
        response = self._create_account()

        assert response.status_code == 200
        self.assertTemplateUsed(response, "registration/authenticate.html")

    def test_creates_user_with_hashed_password(self):
        """The account is created with the chosen username and a hashed password."""
        self._create_account()

        user = User.objects.get_by_natural_key("new-signup-user")
        assert user.check_password(PASSWORD)

    def test_creates_unconfirmed_authenticator_device(self):
        """An unconfirmed authenticator device is created, waiting for confirmation."""
        self._create_account()

        device = self._pending_totp()
        assert device.name == TOTP_DEVICE_NAME

    def test_creates_confirmed_recovery_device(self):
        """The recovery-code device is created confirmed, so it works even if the authenticator step is skipped."""
        self._create_account()

        device = StaticDevice.objects.get(user__username="new-signup-user", name=RECOVERY_DEVICE_NAME)
        assert device.confirmed is True

    def test_shows_ten_recovery_codes_once(self):
        """The authenticator setup page shows the ten plain-text recovery codes."""
        response = self._create_account()

        assert len(response.context["codes"]) == 10

    def test_setup_page_has_qr_code_and_secret(self):
        """The setup page includes the inline QR code and the manual-entry secret."""
        response = self._create_account()

        assert "<svg" in response.context["svg"]
        assert response.context["secret"]

    def test_stores_pending_enrollment_in_session(self):
        """The pending authenticator device is kept in the session, and the codes are kept there encrypted."""
        response = self._create_account()

        assert self.client.session[PENDING_DEVICE_SESSION_KEY] == self._pending_totp().pk
        stored = self.client.session[PENDING_CODES_SESSION_KEY]
        assert stored != response.context["codes"]
        assert response.context["codes"][0] not in stored

    def test_taken_username_is_rejected_in_any_letter_case(self):
        """A username matching an existing account, in any letter case, returns the signup page with status 400."""
        User.objects.create_user(username="TakenName", password=PASSWORD)
        cases = [("exact", "TakenName"), ("lower case", "takenname"), ("upper case", "TAKENNAME")]
        for name, username in cases:
            with self.subTest(case=name):
                response = self._post(**_signup_data(username=username))

                assert response.status_code == 400
                self.assertTemplateUsed(response, "registration/signup.html")
                assert "Username unavailable." in response.context["form"].errors["username"]
        assert User.objects.filter(username=username_hmac("takenname")).count() == 1

    def test_invalid_signup_is_rejected_and_stores_nothing(self):
        """Each invalid form returns status 400 with the error on the right field, creates no account, and leaves no pending enrollment."""
        cases = [
            ("mismatched passwords", {"password2": "different-pass-789"}, ("password2",)),
            ("weak password", {"password1": "123", "password2": "123"}, ("password1", "password2")),
            ("missing username", {"username": ""}, ("username",)),
        ]
        for name, overrides, fields in cases:
            with self.subTest(case=name):
                response = self._post(**_signup_data(**overrides))

                assert response.status_code == 400
                errors = response.context["form"].errors
                assert any(field in errors for field in fields)
                assert not User.objects.filter(username=username_hmac("new-signup-user")).exists()
                assert PENDING_DEVICE_SESSION_KEY not in self.client.session

    def test_locked_recheck_error_shows_form_again(self):
        """If the locked re-check finds the name taken in another letter case, the form is shown again instead of a 500."""
        with patch(
            "backend.views.accounts.signup.create_user_and_devices",
            new_callable=AsyncMock,
            side_effect=ValidationError("Username unavailable."),
        ):
            response = self._create_account()

        assert response.status_code == 400
        self.assertTemplateUsed(response, "registration/signup.html")
        assert "Username unavailable." in response.context["form"].errors["username"]
        assert PENDING_DEVICE_SESSION_KEY not in self.client.session

    def test_integrity_error_shows_form_again(self):
        """If another request takes the username during save, the form is shown again instead of a 500."""
        with patch(
            "backend.views.accounts.signup.create_user_and_devices",
            new_callable=AsyncMock,
            side_effect=IntegrityError,
        ):
            response = self._create_account()

        assert response.status_code == 400
        self.assertTemplateUsed(response, "registration/signup.html")
        assert "Username unavailable." in response.context["form"].errors["username"]
        assert PENDING_DEVICE_SESSION_KEY not in self.client.session


class TestConfirmAuthenticator(SignupViewTestBase):
    """Tests for POST /signup/ with step=authenticate."""

    def setUp(self):
        super().setUp()
        self._create_account()

    def test_correct_code_confirms_and_redirects_to_login(self):
        """A correct code confirms the authenticator and redirects to login."""
        response = self._post(step=ENROLLMENT_STEP, otp_token=_totp_code(self._pending_totp()))

        assert response.status_code == 302
        assert response.url == reverse("api:login")

    def test_correct_code_confirms_authenticator_and_recovery_codes(self):
        """Confirming turns on the authenticator and the recovery codes created with it."""
        self._post(step=ENROLLMENT_STEP, otp_token=_totp_code(self._pending_totp()))

        assert EncryptedTOTPDevice.objects.get(user__username="new-signup-user").confirmed is True
        assert StaticDevice.objects.get(user__username="new-signup-user", name=RECOVERY_DEVICE_NAME).confirmed is True

    def test_correct_code_clears_pending_session(self):
        """Once confirmed, the pending enrollment and its codes leave the session."""
        self._post(step=ENROLLMENT_STEP, otp_token=_totp_code(self._pending_totp()))

        assert PENDING_DEVICE_SESSION_KEY not in self.client.session
        assert PENDING_CODES_SESSION_KEY not in self.client.session

    def test_wrong_code_shows_setup_page_with_error(self):
        """A wrong code shows the setup page again with the invalid-code message and status 400."""
        response = self._post(step=ENROLLMENT_STEP, otp_token="000000")

        assert response.status_code == 400
        self.assertTemplateUsed(response, "registration/authenticate.html")
        assert response.context["error"] == INVALID_CODE_MESSAGE

    def test_wrong_code_keeps_authenticator_unconfirmed(self):
        """A wrong code leaves the authenticator unconfirmed."""
        self._post(step=ENROLLMENT_STEP, otp_token="000000")

        assert self._pending_totp().confirmed is False

    def test_confirm_without_pending_enrollment_redirects_to_signup(self):
        """With no pending setup in the session, confirming sends the user back to signup."""
        self.client.get(self.url)  # abandons the pending setup

        response = self._post(step=ENROLLMENT_STEP, otp_token="123456")

        assert response.status_code == 302
        assert response.url == reverse("api:signup")


class TestSkipAuthenticator(SignupViewTestBase):
    """Tests for POST /signup/ with step=skip."""

    def setUp(self):
        super().setUp()
        self._create_account()

    def test_skip_redirects_to_login(self):
        """Skipping the authenticator step redirects to login."""
        response = self._post(step=SKIP_STEP)

        assert response.status_code == 302
        assert response.url == reverse("api:login")

    def test_skip_removes_setup_keeps_account_and_clears_session(self):
        """Skipping removes the unfinished authenticator setup, keeps the account and its recovery codes,
        and forgets the pending enrollment."""
        self._post(step=SKIP_STEP)

        assert not EncryptedTOTPDevice.objects.filter(user__username="new-signup-user").exists()
        assert User.objects.filter(username=username_hmac("new-signup-user")).exists()
        assert StaticDevice.objects.filter(
            user__username="new-signup-user", name=RECOVERY_DEVICE_NAME, confirmed=True
        ).exists()
        assert PENDING_DEVICE_SESSION_KEY not in self.client.session
        assert PENDING_CODES_SESSION_KEY not in self.client.session

    def test_skip_without_pending_enrollment_redirects_to_signup(self):
        """With no pending setup, skipping sends the user back to signup."""
        self.client.get(self.url)  # abandons the pending setup

        response = self._post(step=SKIP_STEP)

        assert response.status_code == 302
        assert response.url == reverse("api:signup")
