from django.shortcuts import render


def csrf_failure(request, reason=""):
    """Render a friendly page when a CSRF check fails (expired session or stale form)."""
    return render(request, "errors/403_csrf.html", status=403)


# Preview views for the error pages. Only routed when DEBUG is True (see fAIth/urls.py).
def preview_400(request):
    return render(request, "errors/400.html", status=400)


def preview_403(request):
    return render(request, "errors/403.html", status=403)


def preview_403_csrf(request):
    return csrf_failure(request)


def preview_404(request):
    return render(request, "errors/404.html", status=404)


def preview_429(request):
    return render(request, "errors/429.html", status=429)


def preview_500(request):
    return render(request, "errors/500.html", status=500)


def preview_503(request):
    return render(request, "errors/503.html", status=503)
