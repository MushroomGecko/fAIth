"""An AsyncClient that builds requests the way a real ASGI server does, for concurrency tests."""

from django.test import AsyncClient


class ServerAsyncClient(AsyncClient):
    """
    AsyncClient that builds the request scope the way a real ASGI server does.

    The test client differs from a real server in two places the login stack depends on:
    - django_asgi_lifespan's middleware reads scope["state"], which the server sets from its lifespan.
    - The client IP lives in scope["client"]. The test client ignores a REMOTE_ADDR argument there.
    """

    def _base_scope(self, **request):
        scope = super()._base_scope(**request)
        scope["state"] = {}
        scope["client"] = [request.get("REMOTE_ADDR", "127.0.0.1"), 0]
        return scope
