from adrf.views import APIView
from ai.serializers import GeneralQuestionSerializer
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.template.loader import render_to_string
import logging
from rest_framework.permissions import IsAuthenticated
import asyncio
import os
from django.utils.safestring import mark_safe
from ai.utils import async_read_file, stringify_vdb_results, clean_llm_output
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)


MILVUS_SEARCH_LIMIT = int(str(os.getenv("MILVUS_SEARCH_LIMIT", 10)).strip())
RAW_PROMPTS_DIRECTORY = Path("ai", "llm", "prompts")


class GeneralQuestionView(APIView):
    async def post(self, request):
        file_directory = "general_question"
        
        # Validate the request data
        serializer = GeneralQuestionSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Invalid request data: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data.get("query")
        collection_name = serializer.validated_data.get("collection_name")
        if not query or not collection_name:
            logger.error(f"query or collection_name is empty")
            error_message = "Please enter a question!"
            return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

        # Get the pre-initialized Milvus database from lifespan state
        vector_database = request.state["milvus_db"]
        vector_results = await vector_database.search(collection_name=collection_name, query=query, limit=MILVUS_SEARCH_LIMIT)
        stringified_vector_results = await stringify_vdb_results(vector_results)
        logger.info(f"Vector results:\n{stringified_vector_results}")

        # Get the system and user prompts
        system_prompt = await async_read_file(RAW_PROMPTS_DIRECTORY.joinpath(file_directory, "system.md"))
        user_prompt = await async_read_file(RAW_PROMPTS_DIRECTORY.joinpath(file_directory, "user.md"))
        user_prompt = user_prompt.format(query=query, context=stringified_vector_results)
        # Remove whitespace from the prompts
        system_prompt = system_prompt.strip()
        user_prompt = user_prompt.strip()
        logger.info(f"System prompt:\n{system_prompt}")
        logger.info(f"User prompt:\n{user_prompt}")

        # Get the pre-initialized Completions object from lifespan state
        completions_obj = request.state["completions_obj"]
        result = await completions_obj.completions(system_prompt, user_prompt, query)
        logger.info(f"LLM result:\n{result}")

        # Convert any resulting markdown to HTML
        cleaned_result = await clean_llm_output(result)
        logger.info(f"Cleaned result:\n{cleaned_result}")

        # Render the result to a template
        template_name = "partials/general_question.html"
        context = {
            "response_content": mark_safe(cleaned_result),
        }
        rendered_template = render_to_string(template_name, context)

        # Return the result back to the client
        return HttpResponse(rendered_template, status=status.HTTP_200_OK, content_type="text/html")