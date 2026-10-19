"""Tests for the logout endpoint in backend.views.accounts.logout."""

from unittest.mock import AsyncMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

from backend.utils.authentication import TOTP_DEVICE_NAME

User = get_user_model()
PASSWORD = "a-long-test-password-123"


@override_settings(LOGOUT_REDIRECT_URL="/")
class TestLogoutView(TestCase):
    """Tests for POST /logout/."""

    def setUp(self):
        self.url = reverse("api:logout")
        self.user = User.objects.create_user(username="logout-user", password=PASSWORD)
        self.client.force_login(self.user)

    def _is_logged_in(self):
        """Return True if the test client's session holds a logged-in user."""
        return "_auth_user_id" in self.client.session

    def test_clears_whole_session(self):
        """Logout flushes the session, so the OTP device marker is removed too."""
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = "otp_totp.totpdevice/1"
        session.save()

        self.client.post(self.url)

        assert DEVICE_ID_SESSION_KEY not in self.client.session
        assert "_auth_user_id" not in self.client.session

    def test_redirect_target_depends_on_next_value(self):
        """Local next values are followed. Missing, external, and protocol-relative ones fall back to LOGOUT_REDIRECT_URL."""
        cases = [
            ("no next", "", None, "/"),
            ("safe form next", "", {"next": "/books/"}, "/books/"),
            ("safe query next", "?next=/notes/", None, "/notes/"),
            ("form next wins over query next", "?next=/from-query/", {"next": "/from-form/"}, "/from-form/"),
            ("external next", "", {"next": "https://evil.example.com/"}, "/"),
            ("protocol-relative next", "", {"next": "//evil.example.com/"}, "/"),
        ]
        for name, query, data, expected in cases:
            with self.subTest(case=name):
                response = self.client.post(f"{self.url}{query}", data or {})

                assert response.status_code == 302
                assert response.url == expected

    @override_settings(LOGOUT_REDIRECT_URL="/goodbye/")
    def test_uses_configured_logout_redirect_url(self):
        """The default destination comes from LOGOUT_REDIRECT_URL."""
        response = self.client.post(self.url)

        assert response.url == "/goodbye/"

    def test_logged_out_user_posting_is_harmless(self):
        """Posting to logout without a session still redirects and doesn't error."""
        self.client.logout()

        response = self.client.post(self.url)

        assert response.status_code == 302
        assert not self._is_logged_in()

    def test_get_is_rejected_without_logging_out_or_calling_alogout(self):
        """Logout only accepts POST, so a GET returns 405, keeps the session, and never reaches alogout."""
        with patch("backend.views.accounts.logout.alogout", new_callable=AsyncMock) as mock_alogout:
            response = self.client.get(self.url)

        assert response.status_code == 405
        assert self._is_logged_in()
        mock_alogout.assert_not_awaited()

    def test_does_not_delete_authenticator_device(self):
        """Logging out keeps the account's authenticator app."""
        device = TOTPDevice.objects.create(user=self.user, name=TOTP_DEVICE_NAME, confirmed=True)

        self.client.post(self.url)

        assert TOTPDevice.objects.filter(pk=device.pk).exists()


class TestLogoutCallsAlogout(TestCase):
    """Tests that the logout view calls Django's alogout, and only for POST requests."""

    def setUp(self):
        self.url = reverse("api:logout")
        self.user = User.objects.create_user(username="alogout-user", password=PASSWORD)
        self.client.force_login(self.user)

    def test_post_calls_alogout_once_with_request(self):
        """A POST calls alogout exactly once, with the request being handled."""
        with patch("backend.views.accounts.logout.alogout", new_callable=AsyncMock) as mock_alogout:
            self.client.post(self.url)

        mock_alogout.assert_awaited_once()
        assert mock_alogout.await_args.args[0].method == "POST"
