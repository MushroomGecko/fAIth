from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = "a-long-test-password-123"


class TestSignupUsername(TestCase):
    """Tests for username case-insensitivity and the race where two signups save the same name."""

    def _signup(self, username):
        return self.client.post(
            reverse("api:signup"),
            {"username": username, "password1": PASSWORD, "password2": PASSWORD},
        )

    def test_username_differing_only_in_case_is_rejected(self):
        User.objects.create_user(username="Devon", password=PASSWORD)

        response = self._signup("devon")

        self.assertContains(response, "alert alert-danger", status_code=400)
        self.assertContains(response, "A user with that username already exists.", status_code=400)
        self.assertFalse(User.objects.filter(username="devon").exists())

    def test_integrity_error_on_save_shows_form_again(self):
        # Simulates another request saving the same username between the check and the save.
        with patch("backend.views.accounts.signup.create_user_and_devices", side_effect=IntegrityError):
            response = self._signup("racer")

        self.assertContains(response, "A user with that username already exists.", status_code=400)
