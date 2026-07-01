import logging
import os
from pathlib import Path

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from ninja import Form, Router

from ai.serializers.image_search import ImageSearchInputSerializer
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

@router.post("/image_search", tags=[APITags.AI], url_name="image_search")
async def image_search(request, payload: ImageSearchInputSerializer = Form(...)):
    """
    API endpoint for searching for images based on selected text.

    Parameters:
        request: The HTTP request object containing:
            - state["completions_obj"]: Pre-initialized LLM completions object
        payload: Validated request payload containing:
            - selected_text (str): The selected text from the user to search an image for.

    Returns:
        HttpResponse: Rendered HTML template containing the LLM response.
            - 200 OK: HTML template with response_content
            - 400 Bad Request: Validation errors or missing required fields
    """
    file_directory = "image_search"
    
    # Extract validated data from payload
    selected_text = payload.selected_text
    verses_text = payload.verses_text
    book = payload.book
    chapter = payload.chapter

    # Load system and user prompts from files and format with context
    system_prompt = await async_read_file(RAW_PROMPTS_DIRECTORY.joinpath(file_directory, "system.md"))
    user_prompt = await async_read_file(RAW_PROMPTS_DIRECTORY.joinpath(file_directory, "user.md"))
    user_prompt = user_prompt.format(selected_text=selected_text, verses_text=verses_text, book=book, chapter=chapter)
    # Strip leading/trailing whitespace to ensure clean prompt formatting
    system_prompt = system_prompt.strip()
    user_prompt = user_prompt.strip()
    logger.info(f"System prompt:\n{system_prompt}")
    logger.info(f"User prompt:\n{user_prompt}")

    # Use LLM to generate a search query
    completions_obj = request.state["completions_obj"]
    search_query = await completions_obj.completions(system_prompt, user_prompt, selected_text)
    logger.info(f"LLM search query:\n{search_query}")

    # Search for images based on selected text
    image_urls = await search_for_images(search_query, SEARXNG_IMAGE_LIMIT)
    logger.info(f"Image URLs: {image_urls}")

    html_urls = [f"<img src='{url}' style='width: 100%; height: auto; display: block; margin-bottom: 0.5rem;' />\n" for url in image_urls]
    logger.info(f"HTML URLs: {html_urls}")

    # Render the response in an HTML template
    template_name = "partials/text.html"
    context = {
        "response_content": mark_safe("\n".join(html_urls)),
    }
    rendered_template = render_to_string(template_name, context)
    
    # Simply validate the output
    _ = ServerTextResponseSerializer(response_content=rendered_template)
    
    # Return rendered HTML to client
    # 200 - OK
    return HttpResponse(rendered_template, status=200, content_type="text/html")