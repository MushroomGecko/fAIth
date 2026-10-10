from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice

User = get_user_model()
PASSWORD = "a-long-test-password-123"


class TestLoginUsernameCase(TestCase):
    """Login finds the account whatever the letter case of the username."""

    def _login(self, username, password, code=""):
        return self.client.post(reverse("api:login"), {"username": username, "password": password, "otp_token": code})

    def test_password_only_account_logs_in_with_different_case(self):
        user = User.objects.create_user(username="Devon", password=PASSWORD)

        response = self._login("devon", PASSWORD)

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session[SESSION_KEY]), user.pk)

    def test_totp_account_logs_in_with_different_case(self):
        user = User.objects.create_user(username="Mfa", password=PASSWORD)
        device = TOTPDevice.objects.create(user=user, name="Authenticator app", confirmed=True)
        code = str(TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift).token()).zfill(6)

        response = self._login("MFA", PASSWORD, code)

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session[SESSION_KEY]), user.pk)

    def test_wrong_password_with_different_case_does_not_log_in(self):
        User.objects.create_user(username="Devon", password=PASSWORD)

        response = self._login("DEVON", "wrong")

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)
