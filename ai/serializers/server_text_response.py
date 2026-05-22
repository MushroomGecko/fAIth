import logging
from pydantic import BaseModel

# Set up logging
logger = logging.getLogger(__name__)

class ServerTextResponseSerializer(BaseModel):
    """
    Validates and serializes server text response API responses.

    Ensures required fields are present and properly formatted before processing.

    Fields:
        response_content (str): The response content from the LLM.
    """
    response_content: str