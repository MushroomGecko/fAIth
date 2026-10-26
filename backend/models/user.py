import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    The fAIth user account.

    The primary key is a random UUID instead of an incrementing number, so an ID reveals nothing about account
    order or how many accounts exist. Content such as notes and generations should reference this ID.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
