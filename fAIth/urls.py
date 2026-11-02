"""
URL configuration for fAIth project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from functools import partial

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.defaults import bad_request, page_not_found, permission_denied, server_error
from ninja import NinjaAPI

from ai.api import ai_api
from backend.api import backend_api, healcheck_api
from frontend.views.errors import (
    preview_400,
    preview_403,
    preview_403_csrf,
    preview_404,
    preview_429,
    preview_500,
    preview_503,
)

# Create NinjaAPI instance with custom namespace for simpler reverse() calls
api = NinjaAPI(urls_namespace="api")

# Register aggregated app routers with the API
api.add_router("", healcheck_api)
api.add_router("accounts/", backend_api)
api.add_router("v1/", ai_api)

# Django looks for these templates at the template root by default.
# Point each error handler at its template in templates/errors/ instead.
handler400 = partial(bad_request, template_name="errors/400.html")
handler403 = partial(permission_denied, template_name="errors/403.html")
handler404 = partial(page_not_found, template_name="errors/404.html")
handler500 = partial(server_error, template_name="errors/500.html")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("frontend.urls")),
    path("", api.urls),
]

# Debug-only routes to preview every error page in the browser (/400/, /403/, /403_csrf/, /404/, /500/).
# With DEBUG=True, Django shows its own technical pages for real errors, so these let you see the custom ones.
if settings.DEBUG:
    urlpatterns = [
        path("400/", preview_400),
        path("403/", preview_403),
        path("403_csrf/", preview_403_csrf),
        path("404/", preview_404),
        path("429/", preview_429),
        path("500/", preview_500),
        path("503/", preview_503),
    ] + urlpatterns
