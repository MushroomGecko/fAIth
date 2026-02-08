from adrf.serializers import Serializer
from rest_framework import serializers
import logging

# Set up logging
logger = logging.getLogger(__name__)


class GeneralQuestionSerializer(Serializer):
    collection_name = serializers.CharField(max_length=3)
    query = serializers.CharField()

    def validate_query(self, value: str) -> str:
        value = value.strip()
        if not value:
            logger.error("query cannot be empty")
            raise serializers.ValidationError("query cannot be empty")
        return value