import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    The fAIth user account.

    The primary key is a random UUID instead of an incrementing number, so an ID reveals nothing about account
    order or how many accounts exist. Content such as notes and generations should reference this ID.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The PBKDF2-SHA512 hashes (see backend/utils/hashing.py) are about 133 characters, which exceeds
    # AbstractBaseUser's default of 128.
    password = models.CharField(_("password"), max_length=256)
