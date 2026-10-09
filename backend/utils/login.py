from asgiref.sync import sync_to_async
from django.shortcuts import render

# The login page template. render_login() is the only place that renders it.
LOGIN_TEMPLATE = "registration/login.html"


async def render_login(request, form, status=200):
    """
    Render the login form.

    Parameters:
        request (HttpRequest): The current request.
        form (OTPAuthenticationForm): The form to display, with any errors already attached.
        status (int): The HTTP status code for the response (default: 200).

    Returns:
        HttpResponse: The rendered login page.
    """
    # Django's render() is synchronous, so run it in a thread to keep the event loop free.
    return await sync_to_async(render, thread_sensitive=True)(request, LOGIN_TEMPLATE, {"form": form}, status=status)
