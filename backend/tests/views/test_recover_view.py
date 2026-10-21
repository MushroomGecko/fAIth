"""Tests for the account recovery endpoints in backend.views.accounts.recover."""

import asyncio
from datetime import timedelta

from asgiref.sync import async_to_sync
from axes.models import AccessAttempt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from backend.models import EncryptedTOTPDevice
from backend.utils.authentication import (
    LOCKED_OUT_MESSAGE,
    RECOVERY_DEVICE_NAME,
    TOTP_DEVICE_NAME,
    create_recovery_codes,
    hash_recovery_code,
)
from backend.utils.recover import INVALID_RECOVERY_MESSAGE
from backend.utils.signup import PENDING_DEVICE_SESSION_KEY, SKIP_STEP
from fAIth.test_helpers.async_client import ServerAsyncClient

User = get_user_model()
OLD_PASSWORD = "a-long-test-password-123"
NEW_PASSWORD = "another-long-password-456"


class RecoverViewTestBase(TestCase):
    """Shared helpers for the recovery view tests."""

    def setUp(self):
        self.url = reverse("api:recover")
        self.user = User.objects.create_user(username="recover-user", password=OLD_PASSWORD)
        self.codes = async_to_sync(create_recovery_codes)(self.user, confirmed=True)
        self.recovery_device = StaticDevice.objects.get(user=self.user, name=RECOVERY_DEVICE_NAME)

    def _recover(self, **overrides):
        """POST a recovery attempt. Defaults to a correct username, code, and matching new passwords."""
        data = {
            "username": "recover-user",
            "recovery_code": self.codes[0],
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def _code_still_works(self, code):
        """Return True if this recovery code's token still exists on the original device, checked without spending it."""
        token_hash = async_to_sync(hash_recovery_code)(code, self.recovery_device)
        return StaticToken.objects.filter(device_id=self.recovery_device.pk, token=token_hash).exists()


class TestRecoveryPage(RecoverViewTestBase):
    """Tests for GET /recover/."""

    def test_shows_recovery_template_with_unbound_form(self):
        """The recovery page renders its template with an empty, unbound form."""
        response = self.client.get(self.url)

        assert response.status_code == 200
        self.assertTemplateUsed(response, "registration/recover.html")
        assert response.context["form"].is_bound is False

    def test_starts_with_empty_username_and_no_error(self):
        """The page starts with no username and no error message."""
        response = self.client.get(self.url)

        assert response.context["username"] == ""
        assert response.context["error"] is None

    def test_is_never_cached(self):
        """The recovery page is marked no-store, so the browser doesn't keep it."""
        response = self.client.get(self.url)

        assert "no-store" in response["Cache-Control"]


# (name, next value sent, next value the page should keep)
RECOVER_NEXT_CASES = [
    ("local next", "/books/", "/books/"),
    ("external next", "https://evil.example.com/", ""),
    ("protocol-relative next", "//evil.example.com/", ""),
    ("javascript next", "javascript:alert(1)", ""),
    ("no next", "", ""),
]

# (name, next value sent, query string the redirect to login should end with)
RECOVER_REDIRECT_CASES = [
    ("local next", "/books/", "?next=%2Fbooks%2F"),
    ("external next", "https://evil.example.com/", ""),
    ("protocol-relative next", "//evil.example.com/", ""),
    ("javascript next", "javascript:alert(1)", ""),
    ("no next", "", ""),
]


class TestRecoveryKeepsNext(RecoverViewTestBase):
    """The "next" page from login is carried through recovery and back to login."""

    def test_page_keeps_only_local_next(self):
        """The recovery page keeps a local next value in its form and its Back to log in link. Anything else is dropped."""
        login_url = reverse("api:login")
        for name, sent, kept in RECOVER_NEXT_CASES:
            with self.subTest(case=name):
                response = self.client.get(self.url, {"next": sent})

                content = response.content.decode()
                assert response.context["next"] == kept
                assert f'name="next" value="{kept}"' in content
                if kept:
                    assert f'href="{login_url}?next={kept}"' in content
                else:
                    assert f'href="{login_url}"' in content
                if kept:
                    assert f'action="{self.url}?next={kept}"' in content
                else:
                    assert f'action="{self.url}"' in content

    def test_failed_attempt_keeps_only_local_next(self):
        """A failed recovery shows the page again with the same next rules applied."""
        for name, sent, kept in RECOVER_NEXT_CASES:
            with self.subTest(case=name):
                response = self._recover(recovery_code="not-a-real-code", next=sent)

                assert response.status_code == 400
                assert response.context["next"] == kept

    def test_success_and_skip_redirect_to_login_with_only_local_next(self):
        """A successful recovery passes next to the setup step, and skipping it sends the user to login with it."""
        login_url = reverse("api:login")
        codes = self.codes
        for index, (name, sent, suffix) in enumerate(RECOVER_REDIRECT_CASES):
            with self.subTest(case=name):
                # Each recovery changes the password and replaces the codes, so use the newest codes and a new password.
                response = self._recover(
                    recovery_code=codes[0],
                    next=sent,
                    new_password1=f"{NEW_PASSWORD}-{index}",
                    new_password2=f"{NEW_PASSWORD}-{index}",
                )

                assert response.status_code == 200
                assert response.context["next"] == ("/books/" if suffix else "")
                codes = response.context["codes"]

                skip = self.client.post(reverse("api:signup"), {"step": SKIP_STEP, "next": sent})

                assert skip.url == f"{login_url}{suffix}"


class TestRecoverySuccess(RecoverViewTestBase):
    """Tests for a successful POST /recover/."""

    def test_success_shows_authenticator_setup_step(self):
        """A correct username, code, and matching passwords show the authenticator setup step."""
        response = self._recover()

        assert response.status_code == 200
        self.assertTemplateUsed(response, "registration/authenticate.html")

    def test_success_changes_password_and_session_hash(self):
        """The new password works, the old one doesn't, and the session hash changes so other browsers are signed out."""
        before = self.user.get_session_auth_hash()

        self._recover()

        self.user.refresh_from_db()
        assert self.user.check_password(NEW_PASSWORD)
        assert not self.user.check_password(OLD_PASSWORD)
        assert self.user.get_session_auth_hash() != before

    def test_success_uses_up_the_recovery_code(self):
        """The code that was used can't be used again."""
        self._recover()

        assert self._code_still_works(self.codes[0]) is False

    def test_success_issues_ten_new_recovery_codes(self):
        """A fresh set of ten recovery codes is shown on the setup step."""
        response = self._recover()

        assert len(response.context["codes"]) == 10
        assert set(response.context["codes"]).isdisjoint(self.codes)

    def test_success_replaces_recovery_device(self):
        """The old recovery device is replaced by a confirmed one with the new codes."""
        old_device = StaticDevice.objects.get(user=self.user, name=RECOVERY_DEVICE_NAME)

        self._recover()

        assert not StaticDevice.objects.filter(pk=old_device.pk).exists()
        assert StaticDevice.objects.filter(user=self.user, name=RECOVERY_DEVICE_NAME, confirmed=True).exists()

    def test_success_turns_off_authenticator(self):
        """A confirmed authenticator app is turned off after recovery."""
        old = EncryptedTOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=True)

        self._recover()

        assert not EncryptedTOTPDevice.objects.filter(pk=old.pk).exists()
        assert not EncryptedTOTPDevice.objects.filter(user=self.user, confirmed=True).exists()

    def test_success_offers_new_authenticator_setup(self):
        """An unconfirmed authenticator is created so the user can set it up again, and it's pending in the session."""
        self._recover()

        pending = EncryptedTOTPDevice.objects.get(user=self.user, confirmed=False)
        assert self.client.session[PENDING_DEVICE_SESSION_KEY] == pending.pk

    def test_success_with_uppercase_username(self):
        """A username typed in another letter case still recovers the account."""
        response = self._recover(username="RECOVER-USER")

        self.assertTemplateUsed(response, "registration/authenticate.html")

    def test_success_strips_spaces_around_username(self):
        """Spaces around the username are ignored."""
        response = self._recover(username="  recover-user  ")

        self.assertTemplateUsed(response, "registration/authenticate.html")

    def test_recovery_code_cannot_be_reused_after_success(self):
        """After one successful recovery, the same code is refused on the next attempt."""
        self._recover()

        response = self._recover(
            new_password1="yet-another-password-789",
            new_password2="yet-another-password-789",
        )

        assert response.status_code == 400
        assert response.context["error"] == INVALID_RECOVERY_MESSAGE


class TestRecoveryPasswordChecks(RecoverViewTestBase):
    """Tests for the password checks, which run before the recovery code is used."""

    def test_bad_new_passwords_count_toward_the_lockout(self):
        """Mismatched or weak new passwords count as failed attempts, so repeated typos lock the client out."""
        for _ in range(5):
            self._recover(new_password2="different-pass-789")

        response = self._recover()

        assert response.status_code == 429
        assert response.context["error"] == LOCKED_OUT_MESSAGE
        assert self._code_still_works(self.codes[0]) is True

    def test_bad_passwords_get_generic_error_and_keep_password_and_code(self):
        """Mismatched, reused, or weak new passwords return the generic error with no field errors, and the password and code are both kept."""
        cases = [
            ("mismatched", {"new_password2": "different-pass-789"}),
            ("reuses current password", {"new_password1": OLD_PASSWORD, "new_password2": OLD_PASSWORD}),
            ("weak", {"new_password1": "123", "new_password2": "123"}),
        ]
        for name, overrides in cases:
            with self.subTest(case=name):
                response = self._recover(**overrides)

                assert response.status_code == 400
                self.assertTemplateUsed(response, "registration/recover.html")
                assert response.context["error"] == INVALID_RECOVERY_MESSAGE
                assert not response.context["form"].errors
                assert self._code_still_works(self.codes[0]) is True
                self.user.refresh_from_db()
                assert self.user.check_password(OLD_PASSWORD)


class TestRecoveryCodeChecks(RecoverViewTestBase):
    """Tests for the username and recovery code checks."""

    def test_bad_lookups_all_show_same_invalid_message(self):
        """A wrong code, an unknown username, and an account with no recovery codes all get the same message, so accounts aren't revealed."""
        User.objects.create_user(username="no-codes-user", password=OLD_PASSWORD)
        cases = [
            ("wrong code", {"recovery_code": "zzzz9999"}),
            ("unknown username", {"username": "nobody-here"}),
            ("account without recovery codes", {"username": "no-codes-user"}),
        ]
        for name, overrides in cases:
            with self.subTest(case=name):
                response = self._recover(**overrides)

                assert response.status_code == 400
                assert response.context["error"] == INVALID_RECOVERY_MESSAGE
                self.user.refresh_from_db()
                assert self.user.check_password(OLD_PASSWORD)

    def test_failed_recovery_keeps_username_in_form(self):
        """A failed attempt sends the username back so the user doesn't have to retype it."""
        response = self._recover(recovery_code="zzzz9999")

        assert response.context["username"] == "recover-user"

    def test_failed_recovery_leaves_session_without_pending_setup(self):
        """A failed attempt starts no authenticator setup."""
        self._recover(recovery_code="zzzz9999")

        assert PENDING_DEVICE_SESSION_KEY not in self.client.session


class TestRecoveryLockout(RecoverViewTestBase):
    """Tests for the django-axes lockout on POST /recover/. The lockout is per client and shared with login."""

    OTHER_CLIENT = "203.0.113.9"

    def _lock_account_with_wrong_passwords(self):
        """Five wrong passwords on login from this client. Passwords don't touch the recovery-code device."""
        for _ in range(5):
            self.client.post(reverse("api:login"), {"username": "recover-user", "password": "wrong-password-123"})

    def test_locked_account_refuses_correct_code_and_keeps_it(self):
        """A locked account gets the lockout message even with a correct code, and that code is not used up."""
        self._lock_account_with_wrong_passwords()

        response = self._recover()

        assert response.status_code == 429
        assert response.context["error"] == LOCKED_OUT_MESSAGE
        assert self._code_still_works(self.codes[0]) is True
        self.user.refresh_from_db()
        assert self.user.check_password(OLD_PASSWORD)

    def test_other_client_can_still_recover(self):
        """Someone else's guesses from another connection don't stop the real user recovering."""
        self._lock_account_with_wrong_passwords()

        response = self.client.post(
            self.url,
            {
                "username": "recover-user",
                "recovery_code": self.codes[0],
                "new_password1": NEW_PASSWORD,
                "new_password2": NEW_PASSWORD,
            },
            REMOTE_ADDR=self.OTHER_CLIENT,
        )

        assert response.status_code == 200
        self.assertTemplateUsed(response, "registration/authenticate.html")
        assert self._code_still_works(self.codes[0]) is False

    def test_each_wrong_code_counts_toward_the_lockout(self):
        """Every wrong code is counted against the account by axes, so repeated guesses lock that account and client."""
        for _ in range(5):
            self._recover(recovery_code="zzzz9999")

        attempt = AccessAttempt.objects.get(username="recover-user")
        assert attempt.failures_since_start == 5

    def test_lock_lifts_after_cool_off(self):
        """The lock ends after 15 minutes, so a user who was locked out by mistake can recover with a correct code."""
        for _ in range(5):
            self._recover(recovery_code="zzzz9999")
        assert self._recover().status_code == 429
        AccessAttempt.objects.update(attempt_time=timezone.now() - timedelta(minutes=16))

        response = self._recover()

        assert response.status_code == 200
        self.assertTemplateUsed(response, "registration/authenticate.html")
        assert self._code_still_works(self.codes[0]) is False


class TestRecoveryConcurrency(RecoverViewTestBase):
    """Simultaneous wrong recovery codes from one client must not get past the lockout limit."""

    # Enough requests that the lock check and the failure record overlap in at least one run.
    BATCH_SIZE = 20
    CLIENT_IP = "198.51.100.8"

    async def test_simultaneous_wrong_codes_respect_the_failure_limit(self):
        """Fire a batch of wrong recovery codes at once. At most FAILURE_LIMIT of them may get the normal 400 response."""

        async def attempt():
            """Send one wrong-code recovery attempt with its own client, as a separate browser would."""
            response = await ServerAsyncClient().post(
                self.url,
                {
                    "username": "recover-user",
                    "recovery_code": "zzzz9999",
                    "new_password1": NEW_PASSWORD,
                    "new_password2": NEW_PASSWORD,
                },
                REMOTE_ADDR=self.CLIENT_IP,
            )
            return response.status_code

        statuses = await asyncio.gather(*(attempt() for _ in range(self.BATCH_SIZE)))

        assert statuses.count(400) <= settings.AXES_FAILURE_LIMIT, statuses
