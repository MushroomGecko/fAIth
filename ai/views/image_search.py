import logging

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from ninja import Form, Router

from ai.serializers.image_search import ImageSearchInputSerializer
from ai.serializers.server_text_response import ServerTextResponseSerializer
from ai.utils import search_for_images
from fAIth.api_tags import APITags

# Set up logging
logger = logging.getLogger(__name__)

# Create router for ask selected API
router = Router()


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
    # Extract validated data from payload
    selected_text = payload.selected_text

    # Search for images based on selected text
    image_urls = await search_for_images(selected_text)
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