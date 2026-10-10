from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import TestCase
from django.urls import reverse
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from backend.utils.signup import (
    PENDING_CODES_SESSION_KEY,
    PENDING_DEVICE_SESSION_KEY,
    SKIP_STEP,
)

User = get_user_model()
PASSWORD = "a-long-test-password-123"


class TestSkipAuthenticator(TestCase):
    """Tests for skipping the authenticator step and password-only login."""

    def _pending_signup(self, username):
        """Create an unconfirmed account the way signup does, with the pending keys in the session."""
        user = User.objects.create_user(username=username, password=PASSWORD)
        totp = TOTPDevice.objects.create(user=user, name="Authenticator app", confirmed=False)
        StaticDevice.objects.create(user=user, name="Recovery code", confirmed=False)
        session = self.client.session
        session[PENDING_DEVICE_SESSION_KEY] = totp.id
        session[PENDING_CODES_SESSION_KEY] = ["abc"]
        session.save()
        return user

    def test_skip_deletes_unconfirmed_devices_and_clears_session(self):
        user = self._pending_signup("skipper")

        response = self.client.post(reverse("api:signup"), {"step": SKIP_STEP})

        self.assertRedirects(response, reverse("api:login"), fetch_redirect_response=False)
        self.assertFalse(TOTPDevice.objects.filter(user=user).exists())
        self.assertFalse(StaticDevice.objects.filter(user=user).exists())
        self.assertNotIn(PENDING_DEVICE_SESSION_KEY, self.client.session)
        self.assertNotIn(PENDING_CODES_SESSION_KEY, self.client.session)

    def test_skipped_account_logs_in_with_password_only(self):
        user = self._pending_signup("skipper2")
        self.client.post(reverse("api:signup"), {"step": SKIP_STEP})

        response = self.client.post(reverse("api:login"), {"username": user.username, "password": PASSWORD})

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session[SESSION_KEY]), user.pk)

    def test_pending_account_cannot_log_in_with_password_only(self):
        user = self._pending_signup("pending")

        response = self.client.post(reverse("api:login"), {"username": user.username, "password": PASSWORD})

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_wrong_password_does_not_log_in(self):
        user = User.objects.create_user(username="nopass", password=PASSWORD)

        response = self.client.post(reverse("api:login"), {"username": user.username, "password": "wrong"})

        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(response.status_code, 400)
