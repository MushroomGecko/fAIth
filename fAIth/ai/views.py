from adrf.views import APIView
from ai.serializers import VDBSearchSerializer, LLMCompletionsSerializer
from rest_framework.response import Response
from rest_framework import status
import logging
from rest_framework.permissions import IsAuthenticated

# Set up logging
logger = logging.getLogger(__name__)


class VDBSearchView(APIView):
    async def post(self, request):
        serializer = VDBSearchSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Invalid request data: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        collection_name = serializer.validated_data.get("collection_name")
        query = serializer.validated_data.get("query")
        limit = serializer.validated_data.get("limit")
        logger.info(f"Searching for {query} in {collection_name} with limit {limit}")

        # Get the pre-initialized Milvus database from lifespan state
        vector_database = request.state["milvus_db"]
        
        results = await vector_database.search(collection_name=collection_name, query=query, limit=limit)
        return Response(results, status=status.HTTP_200_OK)

class LLMCompletionsView(APIView):
    async def post(self, request):
        serializer = LLMCompletionsSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Invalid request data: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        system_prompt = open("ai/llm/prompts/testing/system.txt", "r").read()
        user_prompt = open("ai/llm/prompts/testing/user.txt", "r").read()
        query = serializer.validated_data.get("query")
        logger.info(f"Generating completion for {query} with system prompt {system_prompt} and user prompt {user_prompt}")

        # Get the pre-initialized Completions object from lifespan state
        completions_obj = request.state["completions_obj"]
        result = await completions_obj.async_completions(system_prompt, user_prompt, query)
        return Response(result, status=status.HTTP_200_OK)