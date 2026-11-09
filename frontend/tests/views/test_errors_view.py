import inspect
from unittest.mock import AsyncMock, patch

import pytest
from django.http import HttpRequest, HttpResponse
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.test import SimpleTestCase

from frontend.views import errors

# Each preview view: (view function, template it renders, status code it returns)
PREVIEW_VIEWS = [
    (errors.preview_400, "errors/400.html", 400),
    (errors.preview_403, "errors/403.html", 403),
    (errors.preview_403_csrf, "errors/403_csrf.html", 403),
    (errors.preview_404, "errors/404.html", 404),
    (errors.preview_429, "errors/429.html", 429),
    (errors.preview_500, "errors/500.html", 500),
    (errors.preview_503, "errors/503.html", 503),
]


class TestCsrfFailure(SimpleTestCase):
    """Tests for csrf_failure, which Django calls when a POST has a bad CSRF token."""

    def test_csrf_failure_renders_session_expired_page_with_403(self):
        """Test that csrf_failure renders the 403_csrf template with status 403."""
        request = HttpRequest()
        with patch("frontend.views.errors.render") as mock_render:
            mock_render.return_value = HttpResponse("Session expired", status=403)

            result = errors.csrf_failure(request)

            mock_render.assert_called_once_with(request, "errors/403_csrf.html", status=403)
            assert result.status_code == 403

    def test_csrf_failure_does_not_show_reason_to_user(self):
        """Test that the reason Django passes in is not sent to the template."""
        request = HttpRequest()
        with patch("frontend.views.errors.render") as mock_render:
            mock_render.return_value = HttpResponse("Session expired", status=403)

            errors.csrf_failure(request, reason="CSRF token missing or incorrect.")

            args, kwargs = mock_render.call_args
            assert "CSRF token missing" not in str(args) + str(kwargs)

    def test_csrf_failure_is_synchronous(self):
        """Test that csrf_failure is a regular function, since Django's CSRF middleware calls it synchronously."""
        assert not inspect.iscoroutinefunction(errors.csrf_failure)


@pytest.mark.asyncio
class TestPreviewViews(SimpleTestCase):
    """Tests for the development preview views for each error page."""

    async def test_each_preview_renders_its_template_with_its_status(self):
        """Test that every preview view renders the expected template and returns the matching status code."""
        for view, template, status in PREVIEW_VIEWS:
            with self.subTest(view=view.__name__):
                request = HttpRequest()
                with patch("frontend.views.errors.async_render", new=AsyncMock()) as mock_render:
                    mock_render.return_value = HttpResponse("page", status=status)

                    result = await view(request)

                    mock_render.assert_awaited_once_with(request, template, {}, status)
                    assert result.status_code == status

    async def test_preview_views_pass_empty_context(self):
        """Test that the preview pages render with no context, since they show static content."""
        request = HttpRequest()
        with patch("frontend.views.errors.async_render", new=AsyncMock()) as mock_render:
            mock_render.return_value = HttpResponse("page", status=404)

            await errors.preview_404(request)

            assert mock_render.await_args.args[2] == {}


class TestErrorTemplatesExist(SimpleTestCase):
    """Check that every template the error views use exists, so the pages can't fail on a missing file."""

    def test_every_error_template_exists(self):
        """Test that each template named in the error views can be loaded."""
        for _view, template, _status in PREVIEW_VIEWS:
            with self.subTest(template=template):
                try:
                    get_template(template)
                except TemplateDoesNotExist:
                    pytest.fail(f"Missing error template: {template}")
