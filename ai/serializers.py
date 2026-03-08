import logging

from adrf.serializers import Serializer
from rest_framework import serializers

# Set up logging
logger = logging.getLogger(__name__)


class GeneralQuestionSerializer(Serializer):
    """
    Validates and deserializes general question API requests.

    Ensures required fields are present and properly formatted before processing.

    Fields:
        collection_name (str): Name of the Milvus collection to search (max 3 chars).
        query (str): User's question or search query (required, non-empty after strip).
    """
    collection_name = serializers.CharField(max_length=3)
    query = serializers.CharField()

    def validate_query(self, value: str) -> str:
        """
        Validate that the query field is not empty after whitespace trimming.

        Parameters:
            value (str): The query string from the request.

        Returns:
            str: Trimmed query string.

        Raises:
            ValidationError: If the query is empty after stripping whitespace.
        """
        value = value.strip()
        if not value:
            logger.error("query cannot be empty")
            raise serializers.ValidationError("query cannot be empty")
        return value