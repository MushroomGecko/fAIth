"""Checks that django-axes counts lockouts by a keyed hash of the client IP, and never stores the raw address."""

import sys
from unittest.mock import patch

from axes.models import AccessAttempt, AccessLog
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = "a-long-test-password-123"


def _username_identifier(username):
    """Return the value django-axes stores for this username on a failed attempt. None means nothing is stored."""
    credentials = {"username": username} if username is not None else None
    return settings.AXES_USERNAME_CALLABLE(RequestFactory().post("/"), credentials)


def _identifier(ip, forwarded=None):
    """Return the value django-axes counts this client by, for a request from ip with an optional X-Forwarded-For header."""
    headers = {"REMOTE_ADDR": ip}
    if forwarded is not None:
        headers["HTTP_X_FORWARDED_FOR"] = forwarded
    return settings.AXES_CLIENT_IP_CALLABLE(RequestFactory().post("/", **headers))


def _settings_module():
    """Return the module that defines axes_ip_identifier. That is where TRUSTED_PROXY_COUNT and SECRET_KEY are read."""
    return sys.modules[settings.AXES_CLIENT_IP_CALLABLE.__module__]


class TestAxesIpIdentifier(TestCase):
    """Tests for the keyed hash that replaces the client IP address in django-axes."""

    def test_same_ip_gives_same_identifier(self):
        """The identifier is stable, so one client always counts against the same lockout."""
        assert _identifier("198.51.100.1") == _identifier("198.51.100.1")

    def test_different_ips_give_different_identifiers(self):
        """Two clients get separate lockout counts."""
        assert _identifier("198.51.100.1") != _identifier("198.51.100.2")

    def test_identifier_is_not_the_raw_ip(self):
        """The raw address never appears in the identifier."""
        assert "198.51.100.1" not in _identifier("198.51.100.1")

    def test_identifier_depends_on_secret_key(self):
        """Without the secret key the identifier can't be recomputed from a known IP."""
        before = _identifier("198.51.100.1")
        with patch.object(_settings_module(), "SECRET_KEY", "a-different-secret-key"):
            assert _identifier("198.51.100.1") != before

    def test_no_proxy_ignores_forwarded_header(self):
        """With no proxy configured, a client-sent X-Forwarded-For can't change the identifier."""
        with patch.object(_settings_module(), "TRUSTED_PROXY_COUNT", 0):
            assert _identifier("10.0.0.1", "203.0.113.9") == _identifier("10.0.0.1")

    def test_one_proxy_uses_the_address_it_appended(self):
        """With one proxy, the client is the last address in X-Forwarded-For. Earlier entries are ignored."""
        with patch.object(_settings_module(), "TRUSTED_PROXY_COUNT", 1):
            assert _identifier("10.0.0.1", "spoofed-entry, 203.0.113.9") == _identifier("203.0.113.9")

    def test_proxy_count_larger_than_chain_uses_first_entry(self):
        """A proxy count bigger than the header uses the first entry, so the request still gets an identifier."""
        with patch.object(_settings_module(), "TRUSTED_PROXY_COUNT", 3):
            assert _identifier("10.0.0.1", "203.0.113.9") == _identifier("203.0.113.9")


class TestRawIpIsNeverStored(TestCase):
    """Checks through the real login endpoint that no raw IP address reaches the axes tables."""

    def setUp(self):
        self.url = reverse("api:login")
        self.user = User.objects.create_user(username="privacy-user", password=PASSWORD)

    def test_failed_login_stores_only_the_identifier(self):
        """A wrong password is recorded under the hashed identifier, not 127.0.0.1."""
        Client().post(
            self.url, {"username": "privacy-user", "password": "wrong-password-123"}, REMOTE_ADDR="198.51.100.1"
        )

        stored = list(AccessAttempt.objects.values_list("ip_address", flat=True))
        assert stored == [_identifier("198.51.100.1")]
        assert "198.51.100.1" not in stored

    def test_successful_login_writes_no_access_log(self):
        """Successful logins aren't logged with their IP address and user agent."""
        Client().post(self.url, {"username": "privacy-user", "password": PASSWORD}, REMOTE_ADDR="198.51.100.1")

        assert AccessLog.objects.count() == 0

    def test_failed_login_stores_hashed_username_not_plain_text(self):
        """The plain username never reaches the failed-attempt table, and the stored value is the keyed hash."""
        Client().post(
            self.url, {"username": "privacy-user", "password": "wrong-password-123"}, REMOTE_ADDR="198.51.100.1"
        )

        stored = list(AccessAttempt.objects.values_list("username", flat=True))
        assert stored == [_username_identifier("privacy-user")]
        assert "privacy-user" not in stored
        assert "privacy-user" not in str(AccessAttempt.objects.values_list("post_data", flat=True))


class TestAxesUsernameIdentifier(SimpleTestCase):
    """Tests for the keyed hash that replaces the username in django-axes records."""

    def test_same_username_gives_same_identifier(self):
        """The identifier is stable, so repeated failures for one username are recorded together."""
        assert _username_identifier("Alice") == _username_identifier("Alice")

    def test_username_case_does_not_change_identifier(self):
        """Signup treats usernames that differ only by case as the same, so the hash does too."""
        assert _username_identifier("Alice") == _username_identifier("alice")

    def test_identifier_is_not_the_plain_username(self):
        """The plain username never appears in the identifier."""
        assert "alice" not in _username_identifier("alice")

    def test_identifier_depends_on_secret_key(self):
        """Without the secret key the identifier can't be recomputed from a known username."""
        before = _username_identifier("alice")
        with patch.object(_settings_module(), "SECRET_KEY", "a-different-secret-key"):
            assert _username_identifier("alice") != before

    def test_no_username_gives_none(self):
        """With no username in the credentials or the form, nothing is stored."""
        assert _username_identifier(None) is None
