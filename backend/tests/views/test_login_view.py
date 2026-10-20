"""Tests for the login page and login endpoint in backend.views.accounts.login."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync
from axes.models import AccessAttempt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from backend.utils.authentication import (
    LOCKED_OUT_MESSAGE,
    RECOVERY_DEVICE_NAME,
    TOTP_DEVICE_NAME,
    create_recovery_codes,
)
from backend.utils.signup import PENDING_CODES_SESSION_KEY, PENDING_DEVICE_SESSION_KEY
from fAIth.test_helpers.async_client import ServerAsyncClient

User = get_user_model()
PASSWORD = "a-long-test-password-123"
LOGIN_ERROR = "TOTP not set up or wrong code entered."


def _totp_code(device):
    """Return the 6-digit code the authenticator app would show for this device right now."""
    return str(TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift).token()).zfill(device.digits)


class LoginViewTestBase(TestCase):
    """Shared helpers for the login view tests."""

    def setUp(self):
        self.url = reverse("api:login")

    def _post(self, **data):
        """POST to the login endpoint with the given form values."""
        return self.client.post(self.url, data)

    def _is_logged_in(self):
        """Return True if the test client's session holds a logged-in user."""
        return "_auth_user_id" in self.client.session


class TestLoginPage(LoginViewTestBase):
    """Tests for GET /login/."""

    def test_shows_login_template(self):
        """The login page renders the login template with status 200."""
        response = self.client.get(self.url)

        assert response.status_code == 200
        self.assertTemplateUsed(response, "registration/login.html")

    def test_form_starts_unbound_without_errors(self):
        """The page starts empty, so the form is unbound and has no errors."""
        response = self.client.get(self.url)

        assert response.context["form"].is_bound is False
        assert response.context["form"].errors == {}

    def test_keeps_only_local_next_for_form_and_signup_link(self):
        """A local next value goes back into the form and the Sign up link. Anything else is dropped."""
        signup_url = reverse("api:signup")
        cases = [
            ("local next", "/books/", "/books/"),
            ("external next", "https://evil.example.com/", ""),
            ("protocol-relative next", "//evil.example.com/", ""),
            ("javascript next", "javascript:alert(1)", ""),
            ("no next", "", ""),
        ]
        for name, sent, kept in cases:
            with self.subTest(case=name):
                response = self.client.get(self.url, {"next": sent})

                assert response.context["next"] == kept
                assert f'name="next" value="{kept}"' in response.content.decode()
                if kept:
                    assert f'action="{self.url}?next={kept}"' in response.content.decode()
                    assert f'href="{signup_url}?next={kept}"' in response.content.decode()
                else:
                    assert f'action="{self.url}"' in response.content.decode()
                    assert f'href="{signup_url}"' in response.content.decode()

    def test_next_is_empty_when_missing(self):
        """Without a next value, the template gets an empty string."""
        response = self.client.get(self.url)

        assert response.context["next"] == ""

    def test_does_not_log_in_anyone(self):
        """Viewing the page doesn't start a session."""
        self.client.get(self.url)

        assert not self._is_logged_in()


class TestLoginPasswordOnly(LoginViewTestBase):
    """Tests for logging in with a password, for accounts without an authenticator app."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="plain-user", password=PASSWORD)

    def test_correct_password_logs_in_and_redirects(self):
        """A correct password for an account with no authenticator app logs the user in."""
        response = self._post(username="plain-user", password=PASSWORD)

        assert response.status_code == 302
        assert response.url == "/"
        assert self._is_logged_in()

    def test_bad_credentials_are_refused(self):
        """Wrong passwords, unknown usernames, and empty forms return the login page with status 400 and no session."""
        cases = [
            ("wrong password", {"username": "plain-user", "password": "wrong-password-123"}),
            ("unknown username", {"username": "nobody-here", "password": PASSWORD}),
            ("missing fields", {}),
        ]
        for name, data in cases:
            with self.subTest(case=name):
                response = self._post(**data)

                assert response.status_code == 400
                self.assertTemplateUsed(response, "registration/login.html")
                assert not self._is_logged_in()

    def test_inactive_account_is_refused(self):
        """A deactivated account can't log in, even with the correct password."""
        self.user.is_active = False
        self.user.save()

        response = self._post(username="plain-user", password=PASSWORD)

        assert response.status_code == 400
        assert not self._is_logged_in()

    def test_username_is_case_insensitive(self):
        """A username typed in a different letter case still logs in."""
        response = self._post(username="PLAIN-USER", password=PASSWORD)

        assert response.status_code == 302
        assert self._is_logged_in()

    def test_next_url_is_followed_only_when_local(self):
        """A local next value sends the user there. An external one is ignored and the user goes to the default page."""
        cases = [
            ("local next", "/books/", "/books/"),
            ("external next", "https://evil.example.com/", "/"),
            ("protocol-relative next", "//evil.example.com/", "/"),
            ("javascript next", "javascript:alert(1)", "/"),
        ]
        for name, next_url, expected in cases:
            with self.subTest(case=name):
                response = self._post(username="plain-user", password=PASSWORD, next=next_url)

                assert response.url == expected

    def test_wrong_password_keeps_next_for_retry(self):
        """A failed login sends next back to the page so the user can retry."""
        response = self._post(username="plain-user", password="wrong-password-123", next="/books/")

        assert response.context["next"] == "/books/"

    def test_code_on_account_without_authenticator_is_refused(self):
        """Sending an authenticator code to an account with no authenticator gives an error and does not log in."""
        response = self._post(username="plain-user", password=PASSWORD, otp_token="123456")

        assert response.status_code == 400
        assert not self._is_logged_in()
        assert LOGIN_ERROR in response.context["form"].non_field_errors()

    def test_wrong_password_with_code_on_plain_account_is_refused(self):
        """A wrong password plus a code is refused and does not log in."""
        response = self._post(username="plain-user", password="wrong-password-123", otp_token="123456")

        assert response.status_code == 400
        assert not self._is_logged_in()

    def test_unfinished_authenticator_setup_is_cleared_on_login(self):
        """A password-only login ends any unfinished authenticator setup for that account."""
        TOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=False)

        self._post(username="plain-user", password=PASSWORD)

        assert not TOTPDevice.objects.filter(user=self.user, confirmed=False).exists()

    def test_unfinished_setup_does_not_block_password_login(self):
        """An unconfirmed authenticator doesn't stop a password-only login."""
        TOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=False)

        response = self._post(username="plain-user", password=PASSWORD)

        assert response.status_code == 302
        assert self._is_logged_in()


class TestLoginWithAuthenticator(LoginViewTestBase):
    """Tests for logging in when the account has a confirmed authenticator app."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="totp-user", password=PASSWORD)
        self.device = TOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=True)

    def test_password_with_correct_code_logs_in(self):
        """A correct password and a valid authenticator code log the user in."""
        response = self._post(username="totp-user", password=PASSWORD, otp_token=_totp_code(self.device))

        assert response.status_code == 302
        assert response.url == "/"
        assert self._is_logged_in()

    def test_code_with_surrounding_spaces_logs_in(self):
        """A code pasted with extra spaces still works."""
        response = self._post(username="totp-user", password=PASSWORD, otp_token=f"  {_totp_code(self.device)} ")

        assert response.status_code == 302
        assert self._is_logged_in()

    def test_bad_combinations_are_refused(self):
        """With an authenticator on, only the right password plus a valid code logs in. Every other combination is refused."""
        recovery_code = async_to_sync(create_recovery_codes)(self.user, confirmed=True)[0]
        good_code = _totp_code(self.device)
        cases = [
            ("password alone", {"username": "totp-user", "password": PASSWORD}),
            ("wrong code", {"username": "totp-user", "password": PASSWORD, "otp_token": "000000"}),
            (
                "wrong password with good code",
                {"username": "totp-user", "password": "wrong-password-123", "otp_token": good_code},
            ),
            (
                "wrong password with wrong code",
                {"username": "totp-user", "password": "wrong-password-123", "otp_token": "000000"},
            ),
            ("recovery code", {"username": "totp-user", "password": PASSWORD, "otp_token": recovery_code}),
        ]
        for name, data in cases:
            with self.subTest(case=name):
                response = self._post(**data)

                assert response.status_code == 400
                assert not self._is_logged_in()

    def test_keeps_only_local_next_after_authenticator_login(self):
        """A login with a correct code goes to the page the user asked for, if it is local. Otherwise the default page."""
        cases = [
            ("local next", "/books/", "/books/"),
            ("external next", "https://evil.example.com/", "/"),
            ("protocol-relative next", "//evil.example.com/", "/"),
            ("no next", "", "/"),
        ]
        for name, sent, expected in cases:
            with self.subTest(case=name):
                # django-otp refuses a code it has already accepted in this time window. Reset it so each case can log in.
                TOTPDevice.objects.filter(pk=self.device.pk).update(last_t=-1)
                self.client.logout()

                response = self._post(
                    username="totp-user", password=PASSWORD, otp_token=_totp_code(self.device), next=sent
                )

                assert response.status_code == 302
                assert response.url == expected

    def test_wrong_code_keeps_local_next_for_retry(self):
        """A failed authenticator login shows the form again with the page to return to still in place."""
        response = self._post(username="totp-user", password=PASSWORD, otp_token="000000", next="/books/")

        assert response.status_code == 400
        assert response.context["next"] == "/books/"

    def test_client_supplied_device_is_overridden(self):
        """The device is always the user's authenticator app, even if the browser sends another device ID."""
        other = StaticDevice.objects.create(user=self.user, name=RECOVERY_DEVICE_NAME, confirmed=True)

        response = self._post(
            username="totp-user",
            password=PASSWORD,
            otp_token=_totp_code(self.device),
            otp_device=other.persistent_id,
        )

        assert response.status_code == 302
        assert self._is_logged_in()

    def test_correct_code_clears_unfinished_setup(self):
        """Logging in with a code also ends any unfinished authenticator setup."""
        TOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=False)

        self._post(username="totp-user", password=PASSWORD, otp_token=_totp_code(self.device))

        assert not TOTPDevice.objects.filter(user=self.user, confirmed=False).exists()
        assert TOTPDevice.objects.filter(pk=self.device.pk, confirmed=True).exists()

    def test_wrong_code_keeps_unfinished_setup(self):
        """A failed login doesn't touch an unfinished authenticator setup."""
        pending = TOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=False)

        self._post(username="totp-user", password=PASSWORD, otp_token="000000")

        assert TOTPDevice.objects.filter(pk=pending.pk).exists()

    def test_error_is_shown_on_wrong_code(self):
        """A wrong code shows the login page again with a form error."""
        response = self._post(username="totp-user", password=PASSWORD, otp_token="000000")

        assert response.status_code == 400
        self.assertTemplateUsed(response, "registration/login.html")
        assert response.context["form"].errors


class TestLoginCallsAlogin(LoginViewTestBase):
    """Tests that the login view calls Django's alogin, only when the login is fully accepted."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="alogin-user", password=PASSWORD)
        self.device = TOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=True)

    def test_password_only_login_calls_alogin_with_user(self):
        """A successful password-only login calls alogin once, with the request and the logged-in user."""
        plain = User.objects.create_user(username="alogin-plain", password=PASSWORD)

        with patch("backend.views.accounts.login.alogin", new_callable=AsyncMock) as mock_alogin:
            self._post(username="alogin-plain", password=PASSWORD)

        mock_alogin.assert_awaited_once()
        request, user = mock_alogin.await_args.args
        assert request.method == "POST"
        assert user.pk == plain.pk

    def test_authenticator_login_calls_alogin_with_user(self):
        """A successful password and code login calls alogin once with the logged-in user."""
        with patch("backend.views.accounts.login.alogin", new_callable=AsyncMock) as mock_alogin:
            self._post(username="alogin-user", password=PASSWORD, otp_token=_totp_code(self.device))

        mock_alogin.assert_awaited_once()
        assert mock_alogin.await_args.args[1].pk == self.user.pk

    def test_refused_logins_do_not_call_alogin(self):
        """Any refused login skips alogin, so no session is started."""
        good_code = _totp_code(self.device)
        cases = [
            ("wrong password", {"username": "alogin-user", "password": "wrong-password-123", "otp_token": good_code}),
            ("wrong code", {"username": "alogin-user", "password": PASSWORD, "otp_token": "000000"}),
            ("password alone", {"username": "alogin-user", "password": PASSWORD}),
        ]
        for name, data in cases:
            with self.subTest(case=name):
                with patch("backend.views.accounts.login.alogin", new_callable=AsyncMock) as mock_alogin:
                    self._post(**data)

                mock_alogin.assert_not_awaited()


class TestLoginClearsPendingRecoveryCodes(LoginViewTestBase):
    """A successful login drops the plain-text recovery codes of any unfinished signup or recovery setup."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="pending-user", password=PASSWORD)

    def _store_pending_codes(self):
        """Put pending recovery codes into the test client's session, as signup or recovery would."""
        session = self.client.session
        session[PENDING_DEVICE_SESSION_KEY] = 1
        session[PENDING_CODES_SESSION_KEY] = ["3fa2c9d1-07b4e8a5-6c1d0f93-b2e75a48"]
        session.save()

    def _pending_keys(self):
        """Return the pending enrollment keys that are still in the test client's session."""
        session = self.client.session
        return [key for key in (PENDING_DEVICE_SESSION_KEY, PENDING_CODES_SESSION_KEY) if key in session]

    def test_password_only_login_clears_pending_codes(self):
        """Logging in with a password, on an account with no authenticator, drops the pending recovery codes."""
        self._store_pending_codes()

        self._post(username="pending-user", password=PASSWORD)

        assert self._is_logged_in()
        assert self._pending_keys() == []

    def test_authenticator_login_clears_pending_codes(self):
        """Logging in with a code also drops the pending recovery codes."""
        TOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=True)
        device = TOTPDevice.objects.get(user=self.user)
        self._store_pending_codes()

        self._post(username="pending-user", password=PASSWORD, otp_token=_totp_code(device))

        assert self._is_logged_in()
        assert self._pending_keys() == []

    def test_failed_login_keeps_pending_codes(self):
        """A refused login doesn't log anyone in, so the pending codes stay for the user's next try."""
        self._store_pending_codes()

        self._post(username="pending-user", password="wrong-password-123")

        assert not self._is_logged_in()
        assert len(self._pending_keys()) == 2


class TestLoginLockout(LoginViewTestBase):
    """Tests for the django-axes lockout on POST /login/. The account has no authenticator, so only passwords are involved."""

    OTHER_CLIENT = "203.0.113.9"

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="lock-user", password=PASSWORD)

    def _post_from(self, ip, **data):
        """POST to the login endpoint from a given client IP."""
        return self.client.post(self.url, data, REMOTE_ADDR=ip)

    def test_one_wrong_password_is_counted_once(self):
        """A wrong password must add one failure, not two. The form's own authenticate() must not count it again."""
        self._post(username="lock-user", password="wrong-password-123")

        assert AccessAttempt.objects.get().failures_since_start == 1

    def test_below_limit_still_allows_correct_password(self):
        """Four wrong passwords don't stop the right one."""
        for _ in range(4):
            self._post(username="lock-user", password="wrong-password-123")

        response = self._post(username="lock-user", password=PASSWORD)

        assert response.status_code == 302
        assert self._is_logged_in()

    def test_five_wrong_passwords_lock_the_account_for_this_client(self):
        """After five wrong passwords, even the right password is refused from the same client, with the lockout message."""
        for _ in range(4):
            self._post(username="lock-user", password="wrong-password-123")
        fifth = self._post(username="lock-user", password="wrong-password-123")
        assert fifth.status_code == 400

        response = self._post(username="lock-user", password=PASSWORD)

        assert response.status_code == 429
        assert LOCKED_OUT_MESSAGE in response.context["form"].non_field_errors()
        assert not self._is_logged_in()

    def test_other_client_can_still_log_in_to_locked_account(self):
        """A real user on their own connection isn't locked out by someone else's guesses."""
        for _ in range(5):
            self._post(username="lock-user", password="wrong-password-123")

        response = self._post_from(self.OTHER_CLIENT, username="lock-user", password=PASSWORD)

        assert response.status_code == 302
        assert self._is_logged_in()

    def test_one_client_cannot_spread_guesses_across_accounts(self):
        """Five wrong guesses over five accounts lock this client out of a sixth account too. Another client still gets in."""
        for index in range(5):
            User.objects.create_user(username=f"spread-{index}", password=PASSWORD)
            self._post(username=f"spread-{index}", password="wrong-password-123")
        User.objects.create_user(username="spread-sixth", password=PASSWORD)

        response = self._post(username="spread-sixth", password=PASSWORD)
        assert response.status_code == 429
        assert not self._is_logged_in()

        response = self._post_from(self.OTHER_CLIENT, username="spread-sixth", password=PASSWORD)
        assert response.status_code == 302

    def test_lock_lifts_after_cool_off(self):
        """The lock ends after 15 minutes, so a genuine user who was locked out by mistake can log in again."""
        for _ in range(5):
            self._post(username="lock-user", password="wrong-password-123")
        AccessAttempt.objects.update(attempt_time=timezone.now() - timedelta(minutes=16))

        response = self._post(username="lock-user", password=PASSWORD)

        assert response.status_code == 302
        assert self._is_logged_in()

    def test_successful_login_does_not_clear_earlier_failures(self):
        """Four wrong passwords, then a right one, leave the count at four. One more wrong password locks the account.

        Clearing the count on success would let someone with their own account reset their IP and keep guessing.
        """
        for _ in range(4):
            self._post(username="lock-user", password="wrong-password-123")
        assert self._post(username="lock-user", password=PASSWORD).status_code == 302
        self.client.logout()

        fifth = self._post(username="lock-user", password="wrong-password-123")
        assert fifth.status_code == 400

        response = self._post(username="lock-user", password=PASSWORD)

        assert response.status_code == 429
        assert not self._is_logged_in()


class TestLoginConcurrency(TestCase):
    """Simultaneous wrong-password logins from one client must not get past the lockout limit."""

    # Enough requests that the lock check and the failure record overlap in at least one run.
    BATCH_SIZE = 20
    CLIENT_IP = "198.51.100.7"

    def setUp(self):
        self.url = reverse("api:login")
        self.user = User.objects.create_user(username="race-user", password=PASSWORD)

    async def test_simultaneous_wrong_passwords_respect_the_failure_limit(self):
        """Fire a batch of wrong passwords at once. At most FAILURE_LIMIT of them may get the normal 400 response."""

        async def attempt():
            """Send one wrong-password login with its own client, as a separate browser would."""
            response = await ServerAsyncClient().post(
                self.url,
                {"username": "race-user", "password": "wrong-password-123"},
                REMOTE_ADDR=self.CLIENT_IP,
            )
            return response.status_code

        statuses = await asyncio.gather(*(attempt() for _ in range(self.BATCH_SIZE)))

        assert statuses.count(400) <= settings.AXES_FAILURE_LIMIT, statuses
