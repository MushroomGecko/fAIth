import logging
import re

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from ninja import Form, Router

from backend.models.note import Note
from backend.serializers.note import (
    DeleteNoteInputSerializer,
    NoteInputSerializer,
    UpdateNoteInputSerializer,
)
from backend.utils.note_html import sanitize_note_html
from fAIth.api_tags import APITags

# Set up logging
logger = logging.getLogger(__name__)

# Create router for note selected API
router = Router()


@router.post("/post_note", tags=[APITags.BACKEND], url_name="post_note")
@csrf_protect
async def post_note(request, payload: NoteInputSerializer = Form(...)):
    """
    Save a note about the selected verses, or a general note about the chapter when nothing is selected.

    Args:
        request: The HTTP request (authenticated user is attached to the note).
        payload: Validated note data (collection_name, book, chapter, verses_text,
            selected_html, note).

    Returns:
        HttpResponse: 200 OK with a plain-text confirmation.
    """
    # Refuse signed-out visitors before anything is built or saved
    user = await request.auser()
    if not user.is_authenticated:
        return HttpResponse("Please sign in to save notes.", status=401, content_type="text/plain")

    # Extract validated data from payload
    collection_name = payload.collection_name
    book = payload.book
    chapter = payload.chapter
    verses_text = payload.verses_text
    # Keep only the allowed spans (e.g. red words of Jesus) so the saved HTML is safe to render
    selected_html = sanitize_note_html(payload.selected_html)
    note = payload.note
    highlight_coordinates = payload.highlight_coordinates
    highlight_color = payload.highlight_color

    # Each verse line starts with its number, e.g. "16) For God so loved...".
    verses_numbers = [int(n) for n in re.findall(r"^\s*(\d+)\)", verses_text, re.MULTILINE)]

    # Save the note to the database
    new_note = Note(
        user=user,
        collection_name=collection_name,
        book=book,
        chapter=chapter,
        verses_text=verses_text,
        verses_numbers=verses_numbers,
        selected_html=selected_html,
        highlight_coordinates=highlight_coordinates,
        highlight_color=highlight_color,
    )
    new_note.set_note(note)
    await new_note.asave()

    # Return success response
    # HX-Refresh tells htmx to reload the whole page so the notes render again
    return HttpResponse(
        "Note saved successfully",
        status=200,
        content_type="text/plain",
        headers={"HX-Refresh": "true"},
    )


@router.post("/update_note", tags=[APITags.BACKEND], url_name="update_note")
@csrf_protect
async def update_note(request, payload: UpdateNoteInputSerializer = Form(...)):
    """
    Update the text of one of the signed-in user's notes.

    Args:
        request: The HTTP request (used to identify the signed-in user).
        payload: Validated update data (note_id, note, highlight_color).

    Returns:
        HttpResponse: 200 OK on success, 401 if not signed in, 404 if the note isn't the user's.
    """
    user = await request.auser()
    if not user.is_authenticated:
        return HttpResponse("Please sign in to edit notes.", status=401, content_type="text/plain")

    # Filtering by user means users can only update their own notes
    note = await Note.objects.filter(id=payload.note_id, user=user).afirst()
    if note is None:
        return HttpResponse("Note not found.", status=404, content_type="text/plain")

    note.set_note(payload.note)
    note.highlight_color = payload.highlight_color
    await note.asave()

    return HttpResponse(
        "Note updated successfully",
        status=200,
        content_type="text/plain",
        headers={"HX-Refresh": "true"},
    )


@router.post("/delete_note", tags=[APITags.BACKEND], url_name="delete_note")
@csrf_protect
async def delete_note(request, payload: DeleteNoteInputSerializer = Form(...)):
    """
    Delete one of the signed-in user's notes.

    Args:
        request: The HTTP request (used to identify the signed-in user).
        payload: Validated delete data (note_id).

    Returns:
        HttpResponse: 200 OK on success, 401 if not signed in, 404 if the note isn't the user's.
    """
    user = await request.auser()
    if not user.is_authenticated:
        return HttpResponse("Please sign in to delete notes.", status=401, content_type="text/plain")

    # Filtering by user confirms ownership before anything is deleted
    note = await Note.objects.filter(id=payload.note_id, user=user).afirst()
    if note is None:
        return HttpResponse("Note not found.", status=404, content_type="text/plain")

    await note.adelete()

    return HttpResponse(
        "Note deleted successfully",
        status=200,
        content_type="text/plain",
        headers={"HX-Refresh": "true"},
    )
