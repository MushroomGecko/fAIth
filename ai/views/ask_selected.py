import logging
import os
from pathlib import Path

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from ninja import Form, Router

from ai.serializers.ask_selected import AskSelectedInputSerializer
from ai.serializers.server_text_response import ServerTextResponseSerializer
from ai.utils import async_read_file, clean_llm_output, stringify_vdb_results, unify_vdb_results
from fAIth.api_tags import APITags

# Set up logging
logger = logging.getLogger(__name__)

# Create router for ask selected API
router = Router()

# Configuration constants
MILVUS_SEARCH_LIMIT = int(str(os.getenv("MILVUS_SEARCH_LIMIT", 10)).strip())
RAW_PROMPTS_DIRECTORY = Path("ai", "llm", "prompts")


@router.post("/ask_selected", tags=[APITags.AI], url_name="ask_selected")
async def ask_selected(request, payload: AskSelectedInputSerializer = Form(...)):
    """
    API endpoint for answering questions about selected text using RAG (Retrieval-Augmented Generation).

    Combines vector database search with LLM completions to provide context-aware answers.
    The workflow: validate input -> search vector DB -> load prompts -> call LLM -> render HTML response.

    Process a user question and return an LLM-generated response with context.

    Workflow:
        1. Validate request payload (selected_text, query and collection_name)
        2. Search vector database for relevant context
        3. Load and format system and user prompts
        4. Call LLM with prompts to generate response
        5. Convert markdown to HTML and render template
        6. Return HTML response to client

    Parameters:
        request: The HTTP request object containing:
            - state["milvus_db"]: Pre-initialized vector database connection
            - state["completions_obj"]: Pre-initialized LLM completions object
        payload: Validated request payload containing:
            - collection_name (str): Milvus vector collection to search
            - selected_text (str): The selected text from the user.
            - query (str): User's question about the selected text

    Returns:
        HttpResponse: Rendered HTML template containing the LLM response.
            - 200 OK: HTML template with response_content
            - 400 Bad Request: Validation errors or missing required fields
    """
    file_directory = "ask_selected"

    # Extract validated data from payload
    selected_text = payload.selected_text
    verses_text = payload.verses_text
    book = payload.book
    chapter = payload.chapter
    collection_name = payload.collection_name
    query = payload.query

    # Search vector database for relevant context
    try:
        vector_database = request.state["milvus_db"]
        # Split in half since we are using two queries
        half_limit = MILVUS_SEARCH_LIMIT // 2
        query_results = await vector_database.search(collection_name=collection_name, query=query, limit=half_limit)
        selected_text_results = await vector_database.search(
            collection_name=collection_name, query=selected_text, limit=half_limit
        )
    except Exception as e:
        logger.error(f"Error searching vector database: {e}")
        return HttpResponse(f"Error searching vector database: {e}", status=500, content_type="text/html")

    # Combine and stringify the results
    try:
        unified_results = await unify_vdb_results(query_results + selected_text_results)
        stringified_unified_results = await stringify_vdb_results(unified_results)
    except Exception as e:
        logger.error(f"Error unifying vector database results: {e}")
        return HttpResponse(f"Error unifying vector database results: {e}", status=500, content_type="text/html")
    logger.info(f"Unified results:\n{stringified_unified_results}")

    # Load system and user prompts from files and format with context
    try:
        system_prompt = await async_read_file(RAW_PROMPTS_DIRECTORY.joinpath(file_directory, "system.md"))
        user_prompt = await async_read_file(RAW_PROMPTS_DIRECTORY.joinpath(file_directory, "user.md"))
        user_prompt = user_prompt.format(
            query=query,
            selected_text=selected_text,
            verses_text=verses_text,
            book=book,
            chapter=chapter,
            collection_name=collection_name,
            context=stringified_unified_results,
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

    # Call LLM with prompts to generate response
    try:
        completions_obj = request.state["completions_obj"]
        result = await completions_obj.completions(system_prompt, user_prompt, query)
        logger.info(f"LLM result:\n{result}")
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        return HttpResponse(f"Error generating LLM response: {e}", status=500, content_type="text/html")

    # Convert markdown to HTML for display
    try:
        cleaned_result = await clean_llm_output(result)
        logger.info(f"Cleaned result:\n{cleaned_result}")
    except Exception as e:
        logger.error(f"Error cleaning LLM output: {e}")
        return HttpResponse(f"Error cleaning LLM output: {e}", status=500, content_type="text/html")

    # Render the response in an HTML template
    try:
        template_name = "partials/text.html"
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
