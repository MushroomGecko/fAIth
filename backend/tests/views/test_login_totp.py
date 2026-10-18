from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

User = get_user_model()
PASSWORD = "a-long-test-password-123"


class TestLoginWithAuthenticatorCode(TestCase):
    """Tests for logging in with the password and an authenticator code submitted together."""

    def setUp(self):
        self.user = User.objects.create_user(username="mfa-user", password=PASSWORD)
        self.device = TOTPDevice.objects.create(user=self.user, name="Authenticator app", confirmed=True)

    def _current_code(self):
        """Return the code the authenticator app would show right now."""
        d = self.device
        return str(TOTP(d.bin_key, d.step, d.t0, d.digits, d.drift).token()).zfill(d.digits)

    def _login(self, **extra):
        data = {"username": self.user.username, "password": PASSWORD, **extra}
        return self.client.post(reverse("api:login"), data)

    def test_password_and_valid_code_logs_in(self):
        response = self._login(otp_token=self._current_code())

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)

    def test_password_and_wrong_code_does_not_log_in(self):
        response = self._login(otp_token="000000")

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_password_without_code_does_not_log_in(self):
        response = self._login()

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_wrong_password_with_valid_code_does_not_log_in(self):
        response = self.client.post(
            reverse("api:login"),
            {"username": self.user.username, "password": "wrong", "otp_token": self._current_code()},
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_recovery_code_does_not_replace_authenticator_code_at_login(self):
        recovery = StaticDevice.objects.create(user=self.user, name="Recovery code", confirmed=True)
        StaticToken.objects.create(device=recovery, token="0123456789abcdef")

        response = self._login(otp_token="0123456789abcdef")

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertTrue(StaticToken.objects.filter(device=recovery).exists())

    def test_unconfirmed_authenticator_is_ignored_and_password_alone_logs_in(self):
        self.device.confirmed = False
        self.device.save()

        response = self._login()

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)
