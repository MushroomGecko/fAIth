"""
Database settings for the whole test suite.

Every test runs against an in-memory SQLite database, so no test reads or writes the real Postgres database.
test_settings.py applies these settings, and pytest loads that module for every test directory.
"""

SQLITE_TEST_DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}


def assert_sqlite(databases):
    """
    Raise if any database would not be SQLite. Guards against a test run that would touch a real database server.

    Parameters:
        databases (dict): The DATABASES setting to check.

    Raises:
        RuntimeError: If any alias uses an engine other than SQLite in memory.
    """
    for alias, config in databases.items():
        if config.get("ENGINE") != "django.db.backends.sqlite3" or config.get("NAME") != ":memory:":
            raise RuntimeError(f"Test database '{alias}' must be in-memory SQLite, not {config.get('ENGINE')}.")
