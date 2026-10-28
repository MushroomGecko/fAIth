import uuid

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.utils.encryption import decrypt_username, encrypt_username
from backend.utils.hashing import username_hmac


class UserManager(DjangoUserManager):
    """
    The user manager. Usernames are stored as an HMAC, so every lookup by username has to hash the name first.
    Creating users goes through set_username(), so the plain name is never written to the username column.
    """

    def _create_user(self, username, email, password, **extra_fields):
        """
        Create and save a user with a username, email, and password. Used by create_user and create_superuser.

        Parameters:
            username (str): The username as typed. It is hashed before it is stored.
            email (str | None): The email address, normalized by Django.
            password (str | None): The raw password, hashed before it is stored.
            **extra_fields: Other model fields to set on the user.

        Returns:
            User: The saved user.

        Raises:
            ValueError: If no username is given.
        """
        if not username:
            raise ValueError("The given username must be set")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_username(username)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, username):
        """
        Return the user with this username. Django's authentication backend calls this with the typed name.

        Parameters:
            username (str): The username as typed. It is hashed before the lookup.

        Returns:
            User: The matching user.

        Raises:
            User.DoesNotExist: If no user has this username, ignoring letter case.
        """
        return self.get(**{self.model.USERNAME_FIELD: username_hmac(username)})


class User(AbstractUser):
    """
    The fAIth user account.

    The primary key is a random UUID instead of an incrementing number, so an ID reveals nothing about account
    order or how many accounts exist. Content such as notes and generations should reference this ID.

    The username is never stored in plain text. The username column holds a keyed HMAC of the lowercase username
    (see backend/utils/hashing.py), which is what lookups compare against. The username is also kept encrypted
    in username_display (see backend/utils/encryption.py), so it can still be shown to the user. Both are built
    from the name after Unicode NFKC normalization, the same normalization Django applies to usernames. Use
    set_username() to set the name, and decrypted_username to read it back.
    """

    objects = UserManager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # username is inherited from AbstractUser: unique, max_length=150, and UnicodeUsernameValidator. It holds the
    # HMAC-SHA512 of the username (128 hex characters), which fits in that 150-character column. The length and
    # character checks on the typed name still run in the form, before the name is hashed.

    # The username as typed, encrypted with Fernet (see backend/utils/encryption.py). Only decrypted_username reads it.
    username_display = models.TextField(editable=False, default="")

    # The PBKDF2-SHA512 hashes (see backend/utils/hashing.py) are about 133 characters, which exceeds
    # AbstractBaseUser's default of 128.
    password = models.CharField(_("password"), max_length=256)

    def set_username(self, username):
        """
        Set the username. Stores its HMAC in username and its encrypted form in username_display.

        The name is normalized with Unicode NFKC first, the same way Django normalizes usernames. Both stored
        values are built from that normalized name, so they match what login and signup look up. For plain ASCII
        names, the normalized name is the same as the one typed.

        Parameters:
            username (str): The username as the user typed it.
        """
        username = self.normalize_username(username)
        self.username = username_hmac(username)
        self.username_display = encrypt_username(username)

    @property
    def decrypted_username(self):
        """
        The username, decrypted from username_display. Use this to show the name to the user.

        The value is the NFKC-normalized name that set_username() stored, which is the typed name for plain ASCII.

        Returns:
            str: The plain username, or an empty string if no username has been set.

        Raises:
            cryptography.fernet.InvalidToken: If username_display wasn't made with USERNAME_ENCRYPTION_KEY.
        """
        if not self.username_display:
            return ""
        return decrypt_username(self.username_display)

    def save(self, *args, **kwargs):
        """
        Save the user, after checking that username is the HMAC of the name in username_display.

        This catches a plain name assigned straight to username, which would otherwise be written to the database
        unhashed. It also catches a username_display that doesn't match username. Use set_username() to change the name.

        Raises:
            ValueError: If username isn't the HMAC of the name in username_display.
        """
        if self.username != username_hmac(self.decrypted_username):
            raise ValueError("Set the username with set_username() before saving the user.")
        super().save(*args, **kwargs)
