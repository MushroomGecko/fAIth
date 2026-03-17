"""
Django settings for the test suite.

Sets the env vars that settings.py requires before importing it, so pytest-django
can load settings during collection without a real .env file present.
These values are test-only stubs and must never be used in production.
"""
import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-production")
os.environ.setdefault("POSTGRES_PASSWORD", "test-only-postgres-password-not-for-production")
os.environ.setdefault("MILVUS_PASSWORD", "test-only-milvus-password-not-for-production")

from fAIth.settings import *  # noqa: F401, F403, E402
