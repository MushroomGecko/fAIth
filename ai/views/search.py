import logging
import os
from pathlib import Path

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from ninja import Form, Router

from ai.serializers.search import SearchInputSerializer
from ai.serializers.server_text_response import ServerTextResponseSerializer
from ai.utils import clean_llm_output, ripgrep_bible
from fAIth.api_tags import APITags

# Set up logging
logger = logging.getLogger(__name__)

# Create router for general question API
router = Router()

# Configuration constants
MILVUS_SEARCH_LIMIT = int(str(os.getenv("MILVUS_SEARCH_LIMIT", 10)).strip())
RAW_PROMPTS_DIRECTORY = Path("ai", "llm", "prompts")


@router.post("/search", tags=[APITags.AI], url_name="search")
async def search(request, payload: SearchInputSerializer = Form(...)):
    """
    API endpoint for searching the vector database and direct search in the Bible given the collection and returning the results.

    Workflow:
        1. Validate request payload (collection_name and query)
        2. Search vector database and direct search in the Bible for relevant context
        3. Return the results

    Parameters:
        request: The HTTP request object containing:
            - state["milvus_db"]: Pre-initialized vector database connection
        payload: Validated request payload containing:
            - query (str): User's search query
            - collection_name (str): Milvus vector collection to search

    Returns:
        HttpResponse: Rendered HTML template containing the LLM response.
            - 200 OK: HTML template with response_content
            - 400 Bad Request: Validation errors or missing required fields
    """
    # Extract validated data from payload
    query = payload.query
    collection_name = payload.collection_name

    vector_results = []
    direct_results = []

    # Search vector database for relevant context
    try:
        vector_database = request.state["milvus_db"]
        vector_results = await vector_database.search(
            collection_name=collection_name, query=query, limit=MILVUS_SEARCH_LIMIT
        )
    except Exception as e:
        logger.error(f"Error searching vector database: {e}")
        return HttpResponse(f"Error searching vector database: {e}", status=500, content_type="text/html")
    logger.info(f"Vector results:\n{vector_results}")
    vector_results_parsed = "\n".join(
        [
            f"- {result['text']} ({result['book']} {result['chapter']}:{result['verse']})\n"
            for result in vector_results
        ]
    )

    # Search the Bible for relevant context
    try:
        direct_results = await ripgrep_bible(query, collection_name)
    except Exception as e:
        logger.error(f"Error searching Bible: {e}")
        return HttpResponse(f"Error searching Bible: {e}", status=500, content_type="text/html")
    logger.info(f"Direct results:\n{direct_results}")
    direct_results_parsed = "\n".join(
        [
            f"- {result['text']} ({result['book']} {result['chapter']}:{result['verse']})\n"
            for result in direct_results
        ]
    )
    final_response = f"##Search results for '{query}'\n\n### AI Search Results\n{vector_results_parsed}\n\n### Direct Search Results\n{direct_results_parsed}"

    # Convert markdown to HTML for display
    try:
        cleaned_result = await clean_llm_output(final_response)
        logger.info(f"Cleaned result:\n{cleaned_result}")
    except Exception as e:
        logger.error(f"Error cleaning LLM output: {e}")
        return HttpResponse(f"Error cleaning LLM output: {e}", status=500, content_type="text/html")

    # Render the response in an HTML template
    try:
        template_name = "partials/server_response_partial.html"
        context = {
            "response_content": mark_safe(cleaned_result),
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
