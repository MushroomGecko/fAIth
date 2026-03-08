import logging

from asgiref.sync import sync_to_async
from django.shortcuts import render, redirect
from django.urls import reverse

# Set up logging
logger = logging.getLogger(__name__)


async def async_render(request, template, context):
    """
    Asynchronously render a Django template without blocking the event loop.

    Parameters:
        request: The HTTP request object.
        template (str): Path to the template file to render.
        context (dict): Context dictionary to pass to the template.

    Returns:
        HttpResponse: Rendered HTML response.
    """
    return await sync_to_async(render, thread_sensitive=False)(request, template, context)

async def async_redirect(url, args=[]):
    """
    Asynchronously redirect to a Django URL without blocking the event loop.

    Parameters:
        url (str): Django URL name to redirect to.
        args (list): Positional arguments to pass to the URL reverser.

    Returns:
        HttpResponseRedirect: Redirect response.
    """
    return await sync_to_async(redirect, thread_sensitive=False)(reverse(url, args=args))