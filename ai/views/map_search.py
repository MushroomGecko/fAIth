import logging
import os
from pathlib import Path

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from ninja import Form, Router

from ai.serializers.map_search import MapSearchInputSerializer
from ai.serializers.server_text_response import ServerTextResponseSerializer
from ai.utils import async_read_file, search_for_images
from fAIth.api_tags import APITags

# Set up logging
logger = logging.getLogger(__name__)

# Create router for ask selected API
router = Router()

# Configuration constants
RAW_PROMPTS_DIRECTORY = Path("ai", "llm", "prompts")
SEARXNG_IMAGE_LIMIT = int(str(os.getenv("SEARXNG_IMAGE_LIMIT", 10)).strip())


@router.post("/map_search", tags=[APITags.AI], url_name="map_search")
async def map_search(request, payload: MapSearchInputSerializer = Form(...)):
    """
    API endpoint for searching for maps based on selected text.

    Parameters:
        request: The HTTP request object containing:
            - state["completions_obj"]: Pre-initialized LLM completions object
        payload: Validated request payload containing:
            - selected_text (str): The selected text from the user to search a map for.
            - verses_text (str): The verses text from the user to search a map for.
            - book (str): The book from the user to search a map for.
            - chapter (str): The chapter from the user to search a map for.
            - collection_name (str): The collection name from the user to search a map for.
    Returns:
        HttpResponse: Rendered HTML template containing the LLM response.
            - 200 OK: HTML template with response_content
            - 400 Bad Request: Validation errors or missing required fields
    """
    file_directory = "map_search"

    # Extract validated data from payload
    selected_text = payload.selected_text
    verses_text = payload.verses_text
    book = payload.book
    chapter = payload.chapter
    collection_name = payload.collection_name

    # Load system and user prompts from files and format with context
    try:
        system_prompt = await async_read_file(RAW_PROMPTS_DIRECTORY.joinpath(file_directory, "system.md"))
        user_prompt = await async_read_file(RAW_PROMPTS_DIRECTORY.joinpath(file_directory, "user.md"))
        user_prompt = user_prompt.format(
            selected_text=selected_text,
            verses_text=verses_text,
            book=book,
            chapter=chapter,
            collection_name=collection_name,
        )
    except Exception as e:
        logger.error(f"Error formatting user prompt: {e}")
        return HttpResponse(f"Error formatting user prompt: {e}", status=500, content_type="text/html")

    # Strip leading/trailing whitespace to ensure clean prompt formatting
    try:
        system_prompt = system_prompt.strip()
        user_prompt = user_prompt.strip()
    except Exception as e:
        logger.error(f"Error stripping whitespace: {e}")
        return HttpResponse(f"Error stripping whitespace: {e}", status=500, content_type="text/html")
    logger.info(f"System prompt:\n{system_prompt}")
    logger.info(f"User prompt:\n{user_prompt}")

    # Use LLM to generate a search query
    try:
        completions_obj = request.state["completions_obj"]
        search_query = await completions_obj.completions(system_prompt, user_prompt)
        logger.info(f"LLM search query:\n{search_query}")
    except Exception as e:
        logger.error(f"Error generating search query: {e}")
        return HttpResponse(f"Error generating search query: {e}", status=500, content_type="text/html")

    # Search for maps based on selected text
    try:
        map_urls = await search_for_images(search_query, SEARXNG_IMAGE_LIMIT)
    except Exception as e:
        logger.error(f"Error searching for maps: {e}")
        return HttpResponse(f"Error searching for maps: {e}", status=500, content_type="text/html")
    html_urls = [
        f"<img src='{url}' style='width: 100%; height: auto; display: block; margin-bottom: 0.5rem;' />\n"
        for url in map_urls
    ]
    logger.info(f"HTML URLs: {html_urls}")

    # Render the response in an HTML template
    try:
        template_name = "partials/server_response_partial.html"
        context = {
            "response_content": mark_safe("\n".join(html_urls)),
        }
        rendered_template = render_to_string(template_name, context)
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        return HttpResponse(f"Error rendering template: {e}", status=500, content_type="text/html")

    # Simply validate the output
    try:
        _ = ServerTextResponseSerializer(response_content=rendered_template)
    except Exception as e:
        logger.error(f"Error validating output: {e}")
        return HttpResponse(f"Error validating output: {e}", status=500, content_type="text/html")

    # Return rendered HTML to client
    # 200 - OK
    return HttpResponse(rendered_template, status=200, content_type="text/html")
