from adrf.serializers import Serializer
from rest_framework import serializers
import logging

# Set up logging
logger = logging.getLogger(__name__)

class VDBSearchSerializer(Serializer):
    collection_name = serializers.CharField(max_length=3)
    query = serializers.CharField()
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=10)

    def validate_collection_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            logger.error(f"collection_name cannot be empty")
            raise serializers.ValidationError("collection_name cannot be empty")
        return value

    def validate_query(self, value: str) -> str:
        value = value.strip()
        if not value:
            logger.error(f"query cannot be empty")
            raise serializers.ValidationError("query cannot be empty")
        return value

class LLMCompletionsSerializer(Serializer):
    query = serializers.CharField()

    def validate_query(self, value: str) -> str:
        value = value.strip()
        if not value:
            logger.error(f"query cannot be empty")
            raise serializers.ValidationError("query cannot be empty")
        return value