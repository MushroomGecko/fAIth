from django.conf import settings
from django.contrib.auth import alogout
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect
from ninja import Router

from backend.utils.login import get_next_url
from fAIth.api_tags import APITags

router = Router()


@router.post("/logout/", tags=[APITags.BACKEND], url_name="logout")
@csrf_protect
async def logout(request):
    """Log out the current user and redirect to the page they were on, or the main site."""
    await alogout(request)
    return redirect(await get_next_url(request, default=settings.LOGOUT_REDIRECT_URL))
