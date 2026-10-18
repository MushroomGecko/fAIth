from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from backend.utils.authentication import hash_recovery_code

User = get_user_model()
PASSWORD = "a-long-test-password-123"


class TestRecoveryCodes(TestCase):
    """Tests for refreshing the recovery codes from the Security section."""

    def setUp(self):
        self.user = User.objects.create_user(username="recovery-user", password=PASSWORD)
        self.client.force_login(self.user)

    def _refresh(self, **data):
        data.setdefault("password", PASSWORD)
        return self.client.post(reverse("api:profile_recovery_codes"), data)

    def test_security_section_shows_refresh_button_without_codes(self):
        response = self.client.get(reverse("api:profile_security"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Get new recovery codes")
        self.assertNotContains(response, "I have written down my codes")

    def test_wrong_password_changes_nothing(self):
        old = StaticDevice.objects.create(user=self.user, name="Recovery code", confirmed=True)
        StaticToken.objects.create(device=old, token="oldtoken00000000")

        response = self._refresh(password="wrong-password")

        self.assertEqual(response.status_code, 400)
        self.assertTrue(StaticToken.objects.filter(device=old, token="oldtoken00000000").exists())
        self.assertFalse(StaticDevice.objects.filter(user=self.user).exclude(pk=old.pk).exists())

    def test_correct_password_returns_new_codes_once(self):
        response = self._refresh()

        self.assertEqual(response.status_code, 200)
        # never_cache sets no-store along with other directives, so check that the directive is present.
        self.assertIn("no-store", response["Cache-Control"])
        self.assertContains(response, "I have written down my codes")
        self.assertNotContains(response, "Get new recovery codes")

    def test_new_codes_are_saved_and_match_their_hashes(self):
        response = self._refresh()

        device = StaticDevice.objects.get(user=self.user)
        self.assertTrue(device.confirmed)
        codes = response.context["recovery_codes"]
        self.assertEqual(len(codes), 10)
        stored = set(StaticToken.objects.filter(device=device).values_list("token", flat=True))
        self.assertEqual(stored, {async_to_sync(hash_recovery_code)(code, device) for code in codes})

    def test_refresh_replaces_old_codes(self):
        old = StaticDevice.objects.create(user=self.user, name="Recovery code", confirmed=True)
        StaticToken.objects.create(device=old, token="oldtoken00000000")

        self._refresh()

        self.assertFalse(StaticDevice.objects.filter(pk=old.pk).exists())
        self.assertFalse(StaticToken.objects.filter(token="oldtoken00000000").exists())
        self.assertEqual(StaticDevice.objects.filter(user=self.user).count(), 1)

    def test_refresh_with_totp_requires_code(self):
        TOTPDevice.objects.create(user=self.user, name="Authenticator app", confirmed=True)

        response = self._refresh()

        self.assertNotContains(response, "I have written down my codes", status_code=400)
        self.assertFalse(StaticDevice.objects.filter(user=self.user).exists())

    def test_codes_stay_saved_when_user_never_clicks_done(self):
        # The "done" button only clears the display, so nothing is saved or undone when it's clicked.
        self._refresh()

        response = self.client.get(reverse("api:profile_security"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "I have written down my codes")
        self.assertTrue(StaticDevice.objects.filter(user=self.user, confirmed=True).exists())
        self.assertEqual(StaticToken.objects.filter(device__user=self.user).count(), 10)
