"""Checks that every POST route in the API is protected by Django's csrf_protect."""

import functools
import inspect

from django.http import HttpResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.views.decorators.csrf import csrf_protect

from fAIth.urls import api


def _all_operations(router):
    """Yield every operation on this router and on the routers nested inside it."""
    for path_view in router.path_operations.values():
        yield from path_view.operations
    for _, child_router, *_ in router._routers:
        yield from _all_operations(child_router)


def _api_operations():
    """Yield every operation registered on the API once, including those on nested routers."""
    seen = set()
    for _, router, *_ in api._routers:
        for op in _all_operations(router):
            if id(op) not in seen:
                seen.add(id(op))
                yield op


def _holds_csrf_middleware(func):
    """
    Return True if a closure of this function holds a CsrfViewMiddleware, directly or one function deeper.

    csrf_protect builds its wrapper with decorator_from_middleware, which keeps the middleware instance in
    the closure of the nested pre-processing function.
    """
    for cell in func.__closure__ or ():
        try:
            value = cell.cell_contents
        except ValueError:
            continue
        if isinstance(value, CsrfViewMiddleware):
            return True
        if inspect.isfunction(value) and value.__closure__:
            for inner_cell in value.__closure__:
                try:
                    if isinstance(inner_cell.cell_contents, CsrfViewMiddleware):
                        return True
                except ValueError:
                    continue
    return False


def _uses_csrf_protect(view_func):
    """Return True if a csrf_protect wrapper appears anywhere in the decorator chain of view_func."""
    func = view_func
    while func is not None:
        if _holds_csrf_middleware(func):
            return True
        func = getattr(func, "__wrapped__", None)
    return False


class TestCsrfProtectDetection:
    """Checks that the detector itself works, so the coverage test below can be trusted."""

    def test_detects_csrf_protect_wrapper(self):
        """A function wrapped in csrf_protect is detected."""

        @csrf_protect
        async def view(request):
            return HttpResponse()

        assert _uses_csrf_protect(view) is True

    def test_detects_csrf_protect_under_other_decorators(self):
        """csrf_protect is still detected when another decorator wraps it."""

        def passthrough(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        @passthrough
        @csrf_protect
        async def view(request):
            return HttpResponse()

        assert _uses_csrf_protect(view) is True

    def test_undecorated_function_is_not_detected(self):
        """A plain function has no csrf_protect wrapper."""

        async def view(request):
            return HttpResponse()

        assert _uses_csrf_protect(view) is False


class TestPostRoutesUseCsrfProtect:
    """Every POST route in the API must be protected by csrf_protect."""

    def test_post_routes_exist(self):
        """Guards against the coverage test passing only because it found no routes."""
        post_operations = [op for op in _api_operations() if "POST" in op.methods]

        assert len(post_operations) > 0

    def test_every_post_route_uses_csrf_protect(self):
        """Any POST route without csrf_protect fails this test and is listed in the message."""
        unprotected = []
        for op in _api_operations():
            if "POST" in op.methods and not _uses_csrf_protect(op.view_func):
                unprotected.append(f"{op.view_func.__module__}.{op.view_func.__qualname__}")

        assert not unprotected, "POST routes missing @csrf_protect: " + ", ".join(sorted(unprotected))
