"""Tests for the custom User model in backend.models.user."""

import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from backend.models import User
from backend.utils.encryption import decrypt_username
from backend.utils.hashing import username_hmac


class TestUsernameStorage(TestCase):
    """Checks that the username is stored as an HMAC, with the typed name kept encrypted for display."""

    def test_username_column_holds_hmac_not_plain_name(self):
        """The username column holds the HMAC of the lowercase name, not the name as typed."""
        user = User.objects.create_user(username="Stored-Name", password="a-long-test-password-123")

        user.refresh_from_db()

        assert user.username == username_hmac("Stored-Name")
        assert user.username != "Stored-Name"

    def test_display_username_is_encrypted(self):
        """username_display is a Fernet token, not the plain name."""
        user = User.objects.create_user(username="Encrypted-Name", password="a-long-test-password-123")

        user.refresh_from_db()

        assert "Encrypted-Name" not in user.username_display
        assert decrypt_username(user.username_display) == "Encrypted-Name"

    def test_decrypted_username_keeps_letter_case(self):
        """After a reload, decrypted_username gives back the name as the user typed it."""
        user = User.objects.create_user(username="Shown-Name", password="a-long-test-password-123")

        reloaded = User.objects.get_by_natural_key("shown-name")

        assert reloaded.decrypted_username == "Shown-Name"
        assert reloaded.pk == user.pk

    def test_natural_key_lookup_ignores_letter_case(self):
        """Logging in with a different letter case finds the same account."""
        user = User.objects.create_user(username="Case-Name", password="a-long-test-password-123")

        assert User.objects.get_by_natural_key("CASE-NAME").pk == user.pk

    def test_natural_key_lookup_raises_for_unknown_name(self):
        """A name no account uses raises DoesNotExist."""
        with self.assertRaises(User.DoesNotExist):
            User.objects.get_by_natural_key("nobody-here")

    def test_set_username_changes_both_stored_values(self):
        """set_username updates the HMAC and the encrypted display name together."""
        user = User.objects.create_user(username="before-name", password="a-long-test-password-123")

        user.set_username("After-Name")
        user.save()
        user.refresh_from_db()

        assert user.username == username_hmac("after-name")
        assert user.decrypted_username == "After-Name"

    def test_save_refuses_user_without_username(self):
        """A user whose username was never set with set_username can't be saved, so no plain name is stored."""
        user = User(password="a-long-test-password-123")

        with self.assertRaises(ValueError):
            user.save()

    def test_save_refuses_plain_name_assigned_to_loaded_user(self):
        """Assigning a plain name to username on a loaded user is refused on save, so it never reaches the database."""
        User.objects.create_user(username="loaded-name", password="a-long-test-password-123")
        user = User.objects.get_by_natural_key("loaded-name")
        user.username = "Plain-Name"

        with self.assertRaises(ValueError):
            user.save()

    def test_save_refuses_display_name_that_does_not_match_username(self):
        """A username_display for a different name than username is refused on save."""
        user = User.objects.create_user(username="first-name", password="a-long-test-password-123")
        other = User.objects.create_user(username="second-name", password="a-long-test-password-123")
        user.username_display = other.username_display

        with self.assertRaises(ValueError):
            user.save()

    def test_decrypted_username_is_empty_when_unset(self):
        """An unsaved user with no username gives an empty display name, not an error."""
        assert User().decrypted_username == ""


class TestUserModel(TestCase):
    """Checks the User model's primary key and the account fields it inherits."""

    def test_is_the_configured_auth_user_model(self):
        """The project's auth setting points at this model, so Django and the app use it for accounts."""
        assert settings.AUTH_USER_MODEL == "backend.User"
        assert get_user_model() is User

    def test_primary_key_is_a_uuid(self):
        """New accounts get a UUID primary key, not an incrementing integer."""
        user = User.objects.create_user(username="uuid-user", password="a-long-test-password-123")

        assert isinstance(user.pk, uuid.UUID)

    def test_primary_key_is_a_random_uuid4(self):
        """The key is random (version 4), so it reveals nothing about account order or count."""
        user = User.objects.create_user(username="random-user", password="a-long-test-password-123")

        assert user.pk.version == 4

    def test_each_user_gets_a_different_primary_key(self):
        """Two accounts never share a primary key."""
        first = User.objects.create_user(username="first-user", password="a-long-test-password-123")
        second = User.objects.create_user(username="second-user", password="a-long-test-password-123")

        assert first.pk != second.pk

    def test_primary_key_survives_a_reload_from_the_database(self):
        """The UUID stored in the database is the same one the object had when it was created."""
        user = User.objects.create_user(username="reload-user", password="a-long-test-password-123")
        original = user.pk

        reloaded = User.objects.get_by_natural_key("reload-user")

        assert reloaded.pk == original
        assert isinstance(reloaded.pk, uuid.UUID)

    def test_username_must_be_unique(self):
        """Two accounts can't use the same username."""
        User.objects.create_user(username="taken-user", password="a-long-test-password-123")

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username="taken-user", password="another-long-password-456")

    def test_password_is_hashed_not_stored_plain(self):
        """The password is stored as a hash that checks correctly, and the plain text isn't stored."""
        user = User.objects.create_user(username="hash-user", password="a-long-test-password-123")

        assert user.password != "a-long-test-password-123"
        assert user.check_password("a-long-test-password-123")
        assert not user.check_password("wrong-password-123")

    def test_new_user_is_active_but_not_staff_or_superuser(self):
        """A new account can log in, but has no admin rights."""
        user = User.objects.create_user(username="plain-account", password="a-long-test-password-123")

        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser
