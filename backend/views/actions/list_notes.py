import logging

from django.views.decorators.csrf import csrf_protect
from ninja import Form, Router

from backend.models.note import Note
from backend.serializers.list_notes import ListNotesInputSerializer
from fAIth.api_tags import APITags
from frontend.utils import async_render

# Set up logging
logger = logging.getLogger(__name__)

# Create router for list notes API
router = Router()


@router.post("/list_notes", tags=[APITags.BACKEND], url_name="list_notes")
@csrf_protect
async def list_notes(request, payload: ListNotesInputSerializer = Form(...)):
    """
    List notes for a given collection, book, and chapter for a given user.

    Args:
        request: The HTTP request (used to identify the signed-in user).
        payload: Validated request data (collection_name, book, chapter).

    Returns:
        HttpResponse: 200 OK with the rendered partials/server_list_notes_partial.html.
    """
    # Extract validated data from payload
    collection_name = payload.collection_name
    book = payload.book
    chapter = payload.chapter

    # List the notes for the given user, collection, book, and chapter
    user = await request.auser()
    notes = []
    if user.is_authenticated:
        notes = [
            note
            async for note in Note.objects.filter(
                user=user, collection_name=collection_name, book=book, chapter=chapter
            ).order_by("verses_numbers")
        ]

    # Render the notes list
    return await async_render(request, "partials/server_list_notes_partial.html", {"notes": notes}, 200)
