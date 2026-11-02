from django.shortcuts import render

from frontend.utils import async_render


def csrf_failure(request, reason=""):
    """
    Render the session-expired page when a CSRF check fails.

    Django calls this through CSRF_FAILURE_VIEW when a POST arrives without a valid CSRF token,
    usually because the session expired or the form was loaded before the session changed.
    This view stays synchronous because Django's CSRF middleware calls it synchronously.

    Parameters:
        request: The HTTP request object that failed the CSRF check.
        reason (str): The reason Django gives for the failure. It is not shown to the user.

    Returns:
        HttpResponse: The 403_csrf error page with status 403.
    """
    return render(request, "errors/403_csrf.html", status=403)


# Preview views for the error pages. Only routed when DEBUG is True (see fAIth/urls.py).
async def preview_400(request):
    """
    Show the 400 Bad Request page for development previews.

    Parameters:
        request: The HTTP request object.

    Returns:
        HttpResponse: The 400 error page with status 400.
    """
    return await async_render(request, "errors/400.html", {}, 400)


async def preview_403(request):
    """
    Show the 403 Access Denied page for development previews.

    Parameters:
        request: The HTTP request object.

    Returns:
        HttpResponse: The 403 error page with status 403.
    """
    return await async_render(request, "errors/403.html", {}, 403)


async def preview_403_csrf(request):
    """
    Show the session-expired page for development previews.

    Parameters:
        request: The HTTP request object.

    Returns:
        HttpResponse: The 403_csrf error page with status 403.
    """
    return await async_render(request, "errors/403_csrf.html", {}, 403)


async def preview_404(request):
    """
    Show the 404 Page Not Found page for development previews.

    Parameters:
        request: The HTTP request object.

    Returns:
        HttpResponse: The 404 error page with status 404.
    """
    return await async_render(request, "errors/404.html", {}, 404)


async def preview_429(request):
    """
    Show the 429 Too Many Requests page for development previews.

    Parameters:
        request: The HTTP request object.

    Returns:
        HttpResponse: The 429 error page with status 429.
    """
    return await async_render(request, "errors/429.html", {}, 429)


async def preview_500(request):
    """
    Show the 500 Server Error page for development previews.

    Parameters:
        request: The HTTP request object.

    Returns:
        HttpResponse: The 500 error page with status 500.
    """
    return await async_render(request, "errors/500.html", {}, 500)


async def preview_503(request):
    """
    Show the 503 Service Unavailable page for development previews.

    Parameters:
        request: The HTTP request object.

    Returns:
        HttpResponse: The 503 error page with status 503.
    """
    return await async_render(request, "errors/503.html", {}, 503)
