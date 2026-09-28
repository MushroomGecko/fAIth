from django.contrib.auth import alogout
from django.shortcuts import redirect
from ninja import Router

from fAIth.api_tags import APITags

router = Router()


@router.post("/logout", tags=[APITags.BACKEND], url_name="logout")
async def logout(request):
    """Log out the current user and redirect to the main site."""
    await alogout(request)
    return redirect("/")
