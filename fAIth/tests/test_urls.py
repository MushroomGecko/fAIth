"""Checks the URL configuration in fAIth/urls.py: error page handlers and the debug-only preview routes."""

import importlib
import string
from unittest.mock import AsyncMock, patch

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404, HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import clear_url_caches, path, resolve, reverse
from django.utils.crypto import get_random_string

import fAIth.urls as project_urls


def _raise_bad_request(request):
    raise SuspiciousOperation("test")


def _raise_forbidden(request):
    raise PermissionDenied("test")


def _raise_not_found(request):
    raise Http404("test")


def _raise_server_error(request):
    raise RuntimeError("test")


def _accept_post(request):
    return HttpResponse("ok")


# A small URLconf used by the error tests. It has routes that raise each error, and it uses the handlers from
# fAIth/urls.py, so the real error pages are what the client receives.
urlpatterns = [
    path("test/bad-request/", _raise_bad_request),
    path("test/forbidden/", _raise_forbidden),
    path("test/not-found/", _raise_not_found),
    path("test/server-error/", _raise_server_error),
    path("test/post/", _accept_post),
]
handler400 = project_urls.handler400
handler403 = project_urls.handler403
handler404 = project_urls.handler404
handler500 = project_urls.handler500


class TestProjectUrlPatterns(TestCase):
    """The normal routes in fAIth/urls.py resolve to the right views."""

    def test_admin_is_mounted_at_admin_path(self):
        """The admin site is served under /admin/, and an anonymous visitor is sent to the admin login."""
        assert reverse("admin:index") == "/admin/"

        response = Client().get("/admin/")

        assert response.status_code == 302
        assert "/admin/login/" in response["Location"]

    def test_frontend_routes_resolve_to_their_views(self):
        """The frontend URLs from frontend/urls.py resolve to the expected views."""
        assert resolve("/").url_name == "default_view"
        assert resolve("/Genesis/").url_name == "book_view"
        assert resolve("/Genesis-1/").url_name == "book_chapter_view"
        assert resolve("/Genesis-1-bsb/").url_name == "full_view"

    def test_healthcheck_router_is_mounted_at_root(self):
        """The healthcheck router from api.add_router("", ...) is served at the site root."""
        url = reverse("api:healthcheck")

        assert url.startswith("/") and not url.startswith("/accounts/") and not url.startswith("/v1/")
        assert resolve(url).namespace == "api"

    def test_accounts_router_is_mounted_under_accounts(self):
        """Routes from the backend router (api.add_router("accounts/", ...)) are served under /accounts/."""
        url = reverse("api:recover")

        assert url.startswith("/accounts/")
        assert resolve(url).namespace == "api"

    def test_ai_router_is_mounted_under_v1(self):
        """Routes from the AI router (api.add_router("v1/", ...)) are served under /v1/."""
        url = reverse("api:search")

        assert url.startswith("/v1/")
        assert resolve(url).namespace == "api"

    def test_healthcheck_returns_200_when_database_is_up(self):
        """A GET to the healthcheck route on a working app returns 200 OK through the API router."""
        with patch("backend.views.healthcheck.check_db", new_callable=AsyncMock):
            response = Client().get(reverse("api:healthcheck"))

        assert response.status_code == 200


@override_settings(ROOT_URLCONF=__name__)
class TestErrorPages(TestCase):
    """Each error page is shown, with its status code, when its error happens on a real request."""

    def test_bad_request_shows_400_page(self):
        """A SuspiciousOperation returns status 400 and the 400 page."""
        response = Client().get("/test/bad-request/")

        assert response.status_code == 400
        self.assertTemplateUsed(response, "errors/400.html")

    def test_permission_denied_shows_403_page(self):
        """A PermissionDenied returns status 403 and the 403 page."""
        response = Client().get("/test/forbidden/")

        assert response.status_code == 403
        self.assertTemplateUsed(response, "errors/403.html")

    def test_missing_page_shows_404_page(self):
        """An Http404 returns status 404 and the 404 page."""
        response = Client().get("/test/not-found/")

        assert response.status_code == 404
        self.assertTemplateUsed(response, "errors/404.html")

    def test_unhandled_exception_shows_500_page(self):
        """An unhandled exception returns status 500 and the 500 page, without the test client re-raising it."""
        response = Client(raise_request_exception=False).get("/test/server-error/")

        assert response.status_code == 500
        self.assertTemplateUsed(response, "errors/500.html")

    def test_post_without_csrf_token_shows_session_expired_page(self):
        """A POST without a CSRF token returns status 403 and the session-expired page from CSRF_FAILURE_VIEW."""
        response = Client(enforce_csrf_checks=True).post("/test/post/", {"name": "value"})

        assert response.status_code == 403
        self.assertTemplateUsed(response, "errors/403_csrf.html")

    def test_post_with_csrf_token_is_not_an_error(self):
        """A POST with a matching CSRF token is accepted, so the session-expired page is not shown for valid requests."""
        token = get_random_string(32, allowed_chars=string.ascii_letters + string.digits)
        client = Client(enforce_csrf_checks=True)
        client.cookies["csrftoken"] = token

        response = client.post("/test/post/", {"csrfmiddlewaretoken": token})

        assert response.status_code == 200


class TestProjectHandlers(TestCase):
    """The handlers in fAIth/urls.py point at the templates in templates/errors/."""

    def test_handlers_use_error_templates(self):
        """Each handler renders its matching template in templates/errors/."""
        assert project_urls.handler400.keywords == {"template_name": "errors/400.html"}
        assert project_urls.handler403.keywords == {"template_name": "errors/403.html"}
        assert project_urls.handler404.keywords == {"template_name": "errors/404.html"}
        assert project_urls.handler500.keywords == {"template_name": "errors/500.html"}


class TestDebugPreviewRoutes(TestCase):
    """The preview routes exist only when DEBUG is on. Each one returns its page with its status code."""

    PREVIEWS = [
        ("/400/", 400, "errors/400.html"),
        ("/403/", 403, "errors/403.html"),
        ("/403_csrf/", 403, "errors/403_csrf.html"),
        ("/404/", 404, "errors/404.html"),
        ("/500/", 500, "errors/500.html"),
        ("/429/", 429, "errors/429.html"),
        ("/503/", 503, "errors/503.html"),
    ]

    def _reload_urls(self, debug):
        """Rebuild fAIth/urls.py with DEBUG set to debug, so the preview routes are added or left out."""
        with override_settings(DEBUG=debug):
            importlib.reload(project_urls)
            clear_url_caches()

    def tearDown(self):
        """Rebuild fAIth/urls.py with DEBUG off, so later tests see the normal URL configuration."""
        self._reload_urls(debug=False)
        super().tearDown()

    def test_preview_routes_show_each_page_when_debug_is_on(self):
        """With DEBUG on, every preview route returns its error page with the matching status code."""
        self._reload_urls(debug=True)

        for url, status, template in self.PREVIEWS:
            with self.subTest(url=url):
                response = Client().get(url)

                assert response.status_code == status
                self.assertTemplateUsed(response, template)

    def test_preview_routes_are_not_registered_when_debug_is_off(self):
        """With DEBUG off, the preview URLs resolve to the normal views instead of the preview views."""
        self._reload_urls(debug=False)

        for url, _status, _template in self.PREVIEWS:
            with self.subTest(url=url):
                match = resolve(url)

                assert not match.func.__name__.startswith("preview_")
