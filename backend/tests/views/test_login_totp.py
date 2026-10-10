import time

from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice

from backend.utils.login import PENDING_LOGIN_SESSION_KEY

User = get_user_model()
PASSWORD = "a-long-test-password-123"


class TestTwoStepLogin(TestCase):
    """Tests for the password step followed by the authenticator code step."""

    def setUp(self):
        self.user = User.objects.create_user(username="mfa-user", password=PASSWORD)
        self.device = TOTPDevice.objects.create(user=self.user, name="Authenticator app", confirmed=True)

    def _current_code(self):
        """Return the code the authenticator app would show right now."""
        d = self.device
        return str(TOTP(d.bin_key, d.step, d.t0, d.digits, d.drift).token()).zfill(d.digits)

    def _password_step(self):
        return self.client.post(reverse("api:login"), {"username": self.user.username, "password": PASSWORD})

    def test_password_step_redirects_to_code_page_without_logging_in(self):
        response = self._password_step()

        self.assertRedirects(response, reverse("api:login_totp"), fetch_redirect_response=False)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertIn(PENDING_LOGIN_SESSION_KEY, self.client.session)

    def test_code_page_renders_after_password_step(self):
        self._password_step()

        response = self.client.get(reverse("api:login_totp"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="otp_token"')

    def test_code_page_redirects_to_login_without_pending_password_step(self):
        response = self.client.get(reverse("api:login_totp"))

        self.assertRedirects(response, reverse("api:login"), fetch_redirect_response=False)

    def test_valid_code_logs_in(self):
        self._password_step()

        response = self.client.post(reverse("api:login_totp"), {"otp_token": self._current_code()})

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)
        self.assertNotIn(PENDING_LOGIN_SESSION_KEY, self.client.session)

    def test_invalid_code_does_not_log_in(self):
        self._password_step()

        response = self.client.post(reverse("api:login_totp"), {"otp_token": "000000"})

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_code_step_without_password_step_does_not_log_in(self):
        response = self.client.post(reverse("api:login_totp"), {"otp_token": self._current_code()})

        self.assertRedirects(response, reverse("api:login"), fetch_redirect_response=False)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_expired_password_step_cannot_be_finished(self):
        self._password_step()
        session = self.client.session
        session[PENDING_LOGIN_SESSION_KEY]["at"] = time.time() - 60 * 60
        session.save()

        response = self.client.post(reverse("api:login_totp"), {"otp_token": self._current_code()})

        self.assertRedirects(response, reverse("api:login"), fetch_redirect_response=False)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_wrong_password_never_reaches_code_step(self):
        response = self.client.post(reverse("api:login"), {"username": self.user.username, "password": "wrong"})

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(PENDING_LOGIN_SESSION_KEY, self.client.session)
