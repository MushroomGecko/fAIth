"""
Django settings for the test suite.

Sets the env vars that settings.py requires before importing it, so pytest-django
can load settings during collection without a real .env file present.
These values are test-only stubs and must never be used in production.
"""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-production")
os.environ.setdefault("RECOVERY_CODE_ENCRYPTION_KEY", "wJTODaOVKgVGXU2Ybv6m7fNJ55y_5Mh7MLp15O8dbqs=")
os.environ.setdefault("TOTP_ENCRYPTION_KEY", "39B7b5GuvdS0NYJUksTx8XCZwIszRGHzRXNry9oFQo8=")
os.environ.setdefault("USERNAME_ENCRYPTION_KEY", "Yq8Vd3WkJbQ1sT6nZ0fLxRmH2cUe4aPgK9wNoB7iDjE=")
os.environ.setdefault("USERNAME_HMAC_KEY", "test-only-username-hmac-key-not-for-production")
os.environ.setdefault("POSTGRES_PASSWORD", "test-only-postgres-password-not-for-production")
os.environ.setdefault("MILVUS_PASSWORD", "test-only-milvus-password-not-for-production")

from fAIth.settings import *  # noqa: F401, F403, E402
from fAIth.test_helpers.test_database import SQLITE_TEST_DATABASES, assert_sqlite  # noqa: E402

# Tests never touch the real database. Every test uses an in-memory SQLite database.
DATABASES = SQLITE_TEST_DATABASES
assert_sqlite(DATABASES)
