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
    collection_name = payload.collection_name
    selected_text = payload.selected_text
    query = payload.query

    # Search vector database for relevant context
    vector_database = request.state["milvus_db"]
    # Split in half since we are using two queries
    half_limit = MILVUS_SEARCH_LIMIT // 2
    query_results = await vector_database.search(collection_name=collection_name, query=query, limit=half_limit)
    selected_text_results = await vector_database.search(collection_name=collection_name, query=selected_text, limit=half_limit)

    # Combine the results
    unified_results = await unify_vdb_results(query_results + selected_text_results)

    # Stringify the results
    stringified_unified_results = await stringify_vdb_results(unified_results)
    logger.info(f"Unified results:\n{stringified_unified_results}")

    # Load system and user prompts from files and format with context
    system_prompt = await async_read_file(RAW_PROMPTS_DIRECTORY.joinpath(file_directory, "system.md"))
    user_prompt = await async_read_file(RAW_PROMPTS_DIRECTORY.joinpath(file_directory, "user.md"))
    user_prompt = user_prompt.format(query=query, selected_text=selected_text, context=stringified_unified_results)
    # Strip leading/trailing whitespace to ensure clean prompt formatting
    system_prompt = system_prompt.strip()
    user_prompt = user_prompt.strip()
    logger.info(f"System prompt:\n{system_prompt}")
    logger.info(f"User prompt:\n{user_prompt}")

    # Call LLM with prompts to generate response
    completions_obj = request.state["completions_obj"]
    result = await completions_obj.completions(system_prompt, user_prompt, query)
    logger.info(f"LLM result:\n{result}")

    # Convert markdown to HTML for display
    cleaned_result = await clean_llm_output(result)
    logger.info(f"Cleaned result:\n{cleaned_result}")

    # Render the response in an HTML template
    template_name = "partials/text.html"
    context = {
        "response_content": mark_safe(cleaned_result),
    }
    rendered_template = render_to_string(template_name, context)

    # Simply validate the output
    _ = ServerTextResponseSerializer(response_content=rendered_template)

    # Return rendered HTML to client
    # 200 - OK
    return HttpResponse(rendered_template, status=200, content_type="text/html")
