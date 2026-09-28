import logging

from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from ninja import Router

from fAIth.api_tags import APITags

# Set up logging
logger = logging.getLogger(__name__)

# Create router for ask selected API
router = Router()


@router.get("/signup", tags=[APITags.BACKEND], url_name="signup")
def signup_page(request):
    """Render the account creation form."""
    return render(request, "registration/signup.html", {"form": UserCreationForm()})


@router.post("/signup", tags=[APITags.BACKEND])
def signup(request):
    """Create an account and redirect to the login page on success."""
    form = UserCreationForm(request.POST)
    if form.is_valid():
        form.save()
        return redirect("login")

    return render(request, "registration/signup.html", {"form": form}, status=400)
