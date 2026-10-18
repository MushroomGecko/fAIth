from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice

User = get_user_model()
PASSWORD = "a-long-test-password-123"


class TestTotpSettings(TestCase):
    """Tests for turning two-factor authentication on and off from the Security section."""

    def setUp(self):
        self.user = User.objects.create_user(username="totp-user", password=PASSWORD)
        self.client.force_login(self.user)

    def _code_for(self, device):
        """Return the code the authenticator app would show right now."""
        return str(TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift).token()).zfill(
            device.digits
        )

    def _enable_on(self):
        """Turn on two-factor authentication directly, for tests that start from an enabled account."""
        return TOTPDevice.objects.create(user=self.user, name="Authenticator app", confirmed=True)

    def _start_setup(self, password=PASSWORD):
        return self.client.post(reverse("api:profile_totp_enable"), {"password": password})

    def test_security_section_shows_turn_on_when_off(self):
        response = self.client.get(reverse("api:profile_security"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Turn on two-factor authentication")

    def test_enable_with_wrong_password_creates_no_device(self):
        response = self._start_setup(password="wrong-password")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())

    def test_enable_with_correct_password_shows_qr_and_pending_device(self):
        response = self._start_setup()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<svg")
        self.assertContains(response, 'name="otp_token"')
        device = TOTPDevice.objects.get(user=self.user)
        self.assertFalse(device.confirmed)

    def test_enable_is_refused_when_already_on(self):
        self._enable_on()

        response = self._start_setup()

        self.assertEqual(response.status_code, 400)
        # The refusal is checked by the device state, not the message text, and no unconfirmed setup is created.
        self.assertFalse(TOTPDevice.objects.filter(user=self.user, confirmed=False).exists())
        self.assertTrue(TOTPDevice.objects.filter(user=self.user, confirmed=True).exists())

    def test_confirm_with_wrong_code_keeps_setup_pending(self):
        self._start_setup()

        response = self.client.post(reverse("api:profile_totp_confirm"), {"otp_token": "000000"})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(TOTPDevice.objects.get(user=self.user).confirmed)

    def test_confirm_with_correct_code_turns_on(self):
        self._start_setup()
        device = TOTPDevice.objects.get(user=self.user)

        response = self.client.post(reverse("api:profile_totp_confirm"), {"otp_token": self._code_for(device)})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Two-factor authentication is on.")
        device.refresh_from_db()
        self.assertTrue(device.confirmed)

    def test_cancel_removes_pending_setup(self):
        self._start_setup()

        response = self.client.post(reverse("api:profile_totp_cancel"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())

    def test_disable_with_wrong_code_keeps_it_on(self):
        self._enable_on()

        response = self.client.post(reverse("api:profile_totp_disable"), {"password": PASSWORD, "otp_token": "000000"})

        self.assertEqual(response.status_code, 400)
        self.assertTrue(TOTPDevice.objects.filter(user=self.user, confirmed=True).exists())

    def test_disable_without_code_keeps_it_on(self):
        self._enable_on()

        response = self.client.post(reverse("api:profile_totp_disable"), {"password": PASSWORD})

        self.assertEqual(response.status_code, 400)
        self.assertTrue(TOTPDevice.objects.filter(user=self.user, confirmed=True).exists())

    def test_disable_with_wrong_password_keeps_it_on(self):
        device = self._enable_on()

        response = self.client.post(
            reverse("api:profile_totp_disable"),
            {"password": "wrong-password", "otp_token": self._code_for(device)},
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(TOTPDevice.objects.filter(user=self.user, confirmed=True).exists())

    def test_disable_with_password_and_code_turns_off(self):
        device = self._enable_on()

        response = self.client.post(
            reverse("api:profile_totp_disable"),
            {"password": PASSWORD, "otp_token": self._code_for(device)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Two-factor authentication is off.")
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())

    def _enable_with_recovery_codes(self):
        """Turn on two-factor authentication and create a confirmed recovery-code device. Returns the TOTP device and the codes."""
        from asgiref.sync import async_to_sync

        from backend.utils.account import replace_recovery_codes

        device = self._enable_on()
        # async_to_sync keeps the database work on this thread, so it uses the same test database connection.
        codes = async_to_sync(replace_recovery_codes)(self.user)
        return device, codes

    def test_disable_with_recovery_code_turns_off(self):
        _, codes = self._enable_with_recovery_codes()

        response = self.client.post(
            reverse("api:profile_totp_disable"),
            {"password": PASSWORD, "recovery_code": codes[0]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Two-factor authentication is off.")
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())

    def test_disable_with_recovery_code_alone_needs_no_password(self):
        _, codes = self._enable_with_recovery_codes()

        response = self.client.post(
            reverse("api:profile_totp_disable"),
            {"recovery_code": codes[0]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Two-factor authentication is off.")
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())

    def test_disable_with_both_codes_is_refused_and_keeps_recovery_code(self):
        from django_otp.plugins.otp_static.models import StaticToken

        device, codes = self._enable_with_recovery_codes()
        tokens_before = StaticToken.objects.filter(device__user=self.user).count()

        response = self.client.post(
            reverse("api:profile_totp_disable"),
            {"password": PASSWORD, "otp_token": self._code_for(device), "recovery_code": codes[0]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "not both", status_code=400)
        self.assertTrue(TOTPDevice.objects.filter(user=self.user, confirmed=True).exists())
        self.assertEqual(StaticToken.objects.filter(device__user=self.user).count(), tokens_before)

    def test_disable_with_wrong_recovery_code_keeps_it_on(self):
        self._enable_with_recovery_codes()

        response = self.client.post(
            reverse("api:profile_totp_disable"),
            {"password": PASSWORD, "recovery_code": "not-a-real-code"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "That recovery code is not correct.", status_code=400)
        self.assertTrue(TOTPDevice.objects.filter(user=self.user, confirmed=True).exists())

    def test_opening_security_keeps_unfinished_setup(self):
        self._start_setup()

        self.client.get(reverse("api:profile_security"))

        self.assertTrue(TOTPDevice.objects.filter(user=self.user, confirmed=False).exists())

    def test_opening_account_section_clears_unfinished_setup(self):
        self._start_setup()

        response = self.client.get(reverse("api:profile_account"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())

    def test_opening_profile_page_clears_unfinished_setup(self):
        self._start_setup()

        self.client.get(reverse("api:profile"))

        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())

    def test_password_login_clears_unfinished_setup(self):
        self._start_setup()
        self.client.logout()

        response = self.client.post(reverse("api:login"), {"username": self.user.username, "password": PASSWORD})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())

    def test_clearing_setup_keeps_confirmed_device(self):
        self._enable_on()

        self.client.get(reverse("api:profile_account"))

        self.assertTrue(TOTPDevice.objects.filter(user=self.user, confirmed=True).exists())
