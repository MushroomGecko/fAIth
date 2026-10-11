from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice

User = get_user_model()
PASSWORD = "a-long-test-password-123"
NEW_PASSWORD = "a-brand-new-test-password-456"


class TestChangePassword(TestCase):
    """Tests for changing the logged-in user's password from the Security section."""

    def setUp(self):
        self.user = User.objects.create_user(username="pw-user", password=PASSWORD)
        self.client.force_login(self.user)
        self.url = reverse("api:profile_password")

    def _post(self, **overrides):
        data = {
            "password": PASSWORD,
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def _refresh(self):
        self.user.refresh_from_db()

    def test_security_section_shows_password_form(self):
        response = self.client.get(reverse("api:profile_security"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="new_password1"')
        self.assertContains(response, 'name="new_password2"')

    def test_correct_current_password_changes_password(self):
        response = self._post()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your password was changed.")
        self._refresh()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertFalse(self.user.check_password(PASSWORD))

    def test_user_stays_logged_in_after_change(self):
        self._post()

        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)

    def test_wrong_current_password_does_not_change_password(self):
        response = self._post(password="wrong-password")

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "That password is not correct.")
        self._refresh()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_missing_current_password_does_not_change_password(self):
        response = self._post(password="")

        self.assertEqual(response.status_code, 400)
        self._refresh()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_mismatched_new_passwords_do_not_change_password(self):
        response = self._post(new_password2="a-different-test-password-789")

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "The two passwords do not match.")
        self._refresh()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_same_as_current_password_is_rejected(self):
        response = self._post(new_password1=PASSWORD, new_password2=PASSWORD)

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "different from your current one")
        self._refresh()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_weak_new_password_is_rejected(self):
        response = self._post(new_password1="short", new_password2="short")

        self.assertEqual(response.status_code, 400)
        self._refresh()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_totp_account_requires_code(self):
        TOTPDevice.objects.create(user=self.user, name="Authenticator app", confirmed=True)

        response = self._post()

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Enter the 6-digit code")
        self._refresh()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_totp_account_with_valid_code_changes_password(self):
        device = TOTPDevice.objects.create(user=self.user, name="Authenticator app", confirmed=True)
        code = str(TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift).token()).zfill(
            device.digits
        )

        response = self._post(otp_token=code)

        self.assertEqual(response.status_code, 200)
        self._refresh()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_totp_account_with_wrong_code_does_not_change_password(self):
        TOTPDevice.objects.create(user=self.user, name="Authenticator app", confirmed=True)

        response = self._post(otp_token="000000")

        self.assertEqual(response.status_code, 400)
        self._refresh()
        self.assertTrue(self.user.check_password(PASSWORD))
