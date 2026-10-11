from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from ninja import Router

from fAIth.api_tags import APITags

# Create router for account endpoints
router = Router()


@router.get("/profile/", tags=[APITags.BACKEND], url_name="profile")
@login_required
def account_page(request):
    """
    Show the profile page. Anonymous users are redirected to the login page.
    """
    return render(request, "account/index.html")
