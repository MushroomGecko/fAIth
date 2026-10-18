from django.conf import settings
from django.db import connections

# Run the backend database tests on an in-memory SQLite database, so they don't need a Postgres server.
# This file is loaded only for tests under backend/tests.
settings.DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}
# Django caches the settings and any connection created from them, so drop both and let them rebuild.
for _connection in connections.all(initialized_only=True):
    _connection.close()
    del connections[_connection.alias]
connections.settings = connections.configure_settings(settings.DATABASES)
