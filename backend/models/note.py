import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models

from backend.models.user import User


class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    collection_name = models.CharField(max_length=4)
    book = models.CharField(max_length=32)
    chapter = models.IntegerField()
    verses_text = models.TextField()
    selected_text = models.TextField()
    verses_numbers = ArrayField(models.IntegerField())
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
