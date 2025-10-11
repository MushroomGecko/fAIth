from adrf.views import APIView
from ai.globals import get_milvus_db
from ai.serializers import VDBSearchSerializer
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

        vector_database = await get_milvus_db()
        results = await vector_database.search(collection_name=collection_name, query=query, limit=limit)
        return Response(results, status=status.HTTP_200_OK)
