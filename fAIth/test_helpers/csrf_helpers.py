"""Helpers for tests that call views directly with a hand-built request."""

from django.conf import settings
from django.http import HttpRequest, QueryDict
from django.middleware.csrf import get_token


def add_csrf_token(request: HttpRequest) -> HttpRequest:
    """
    Give a hand-built request the same CSRF cookie and form token that a rendered page would send.

    Views wrapped in csrf_protect then accept the request for the right reason, and the check still runs.
    Only a token that matches the cookie passes.

    Parameters:
        request (HttpRequest): The request to update.

    Returns:
        HttpRequest: The same request, with a CSRF cookie and csrfmiddlewaretoken in POST.
    """
    token = get_token(request)
    request.COOKIES[settings.CSRF_COOKIE_NAME] = request.META["CSRF_COOKIE"]
    request.POST = QueryDict(mutable=True)
    request.POST["csrfmiddlewaretoken"] = token
    return request
