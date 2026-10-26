"""Tests for the custom User model in backend.models.user."""

import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from backend.models import User


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

        reloaded = User.objects.get(username="reload-user")

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
