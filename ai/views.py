from adrf.views import APIView
from ai.serializers import GeneralQuestionSerializer
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
import logging
from rest_framework.permissions import IsAuthenticated
import asyncio
from pathlib import Path

from ai.utils import async_read_file, stringify_vdb_results, clean_llm_output

# Set up logging
logger = logging.getLogger(__name__)


VDB_SEARCH_LIMIT = 10
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
        vector_results = await vector_database.search(collection_name=collection_name, query=query, limit=VDB_SEARCH_LIMIT)
        stringified_vector_results = await stringify_vdb_results(vector_results)
        logger.info(f"Vector results:\n{stringified_vector_results}")

        # Get the system and user prompts
        system_prompt = await async_read_file(Path(RAW_PROMPTS_DIRECTORY, file_directory, "system.txt"))
        user_prompt = await async_read_file(Path(RAW_PROMPTS_DIRECTORY, file_directory, "user.txt"))
        user_prompt = user_prompt.format(query=query, context=stringified_vector_results)

        # Get the pre-initialized Completions object from lifespan state
        completions_obj = request.state["completions_obj"]
        result = await completions_obj.async_completions(system_prompt, user_prompt, query)

        logger.info(f"LLM result:\n{result}")

        # Convert any resulting markdown to HTML
        cleaned_result = await clean_llm_output(result)

        logger.info(f"Cleaned result:\n{cleaned_result}")

        # Return the result back to the client
        return HttpResponse(cleaned_result, status=status.HTTP_200_OK, content_type="text/html")