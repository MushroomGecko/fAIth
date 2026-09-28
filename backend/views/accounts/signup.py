import logging

from asgiref.sync import sync_to_async
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from ninja import Router

from fAIth.api_tags import APITags

# Set up logging
logger = logging.getLogger(__name__)

# Create router for ask selected API
router = Router()


@router.get("/signup", tags=[APITags.BACKEND], url_name="signup")
async def signup_page(request):
    """Render the account creation form."""
    form = await sync_to_async(UserCreationForm, thread_sensitive=True)()
    return await sync_to_async(render, thread_sensitive=True)(request, "registration/signup.html", {"form": form})


@router.post("/signup", tags=[APITags.BACKEND])
async def signup(request):
    """Create an account and redirect to the login page on success."""
    form = await sync_to_async(UserCreationForm, thread_sensitive=True)(request.POST)
    is_valid = await sync_to_async(form.is_valid, thread_sensitive=True)()
    if is_valid:
        await sync_to_async(form.save, thread_sensitive=True)()
        return redirect("login")

    return await sync_to_async(render, thread_sensitive=True)(
        request, "registration/signup.html", {"form": form}, status=400
    )
