"""Tests for the healthcheck endpoint in backend.views.healthcheck."""

import json
from unittest.mock import AsyncMock, patch

from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse


class HealthcheckViewTestBase(TestCase):
    """Shared setup for the healthcheck tests."""

    def setUp(self):
        self.url = reverse("api:healthcheck")


class TestHealthcheckHealthy(HealthcheckViewTestBase):
    """Tests for GET /healthcheck when the app and database are working."""

    def test_returns_ok_status_and_json(self):
        """With a working database, the endpoint returns 200 and {"status": "OK"} as JSON."""
        response = self.client.get(self.url)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"
        assert json.loads(response.content) == {"status": "OK"}

    def test_checks_database_before_returning_ok(self):
        """The database check runs on every request, so OK means the database answered."""
        with patch("backend.views.healthcheck.check_db", new_callable=AsyncMock) as mock_check:
            response = self.client.get(self.url)

        mock_check.assert_awaited_once()
        assert response.status_code == 200


class TestHealthcheckUnhealthy(HealthcheckViewTestBase):
    """Tests for GET /healthcheck when the database check fails."""

    def test_failures_return_503_with_error_message(self):
        """Any failure during the database check returns 503 with status error and the exception message."""
        cases = [
            ("database error", OperationalError("database is locked")),
            ("unexpected error", RuntimeError("connection pool exhausted")),
        ]
        for name, error in cases:
            with self.subTest(case=name):
                with patch("backend.views.healthcheck.check_db", new_callable=AsyncMock, side_effect=error):
                    response = self.client.get(self.url)

                assert response.status_code == 503
                assert response["Content-Type"] == "application/json"
                assert json.loads(response.content) == {"status": "error", "message": str(error)}

    def test_failure_is_logged(self):
        """A failed check is logged as an error, so operators can find it."""
        with patch(
            "backend.views.healthcheck.check_db",
            new_callable=AsyncMock,
            side_effect=RuntimeError("connection pool exhausted"),
        ):
            with self.assertLogs("backend.views.healthcheck", level="ERROR") as logs:
                self.client.get(self.url)

        assert "Healthcheck failed: connection pool exhausted" in logs.output[0]


class TestHealthcheckMethods(HealthcheckViewTestBase):
    """Tests for which HTTP methods the healthcheck accepts."""

    def test_post_is_not_allowed(self):
        """Only GET is served, so a POST returns 405."""
        response = self.client.post(self.url)

        assert response.status_code == 405
