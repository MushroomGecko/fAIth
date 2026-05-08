import logging

from pydantic import BaseModel, field_validator

# Set up logging
logger = logging.getLogger(__name__)


class AskSelectedInputSerializer(BaseModel):
    """
    Validates and deserializes ask selected API requests.

    Ensures required fields are present and properly formatted before processing.

    Fields:
        collection_name (str): Name of the Milvus collection to search (max 3 chars).
        selected_text (str): The selected text from the user.
        query (str): User's question or search query (required, non-empty after strip).
    """
    collection_name: str
    selected_text: str
    query: str

    @field_validator("collection_name")
    @classmethod
    def validate_collection_name(cls, value: str) -> str:
        """
        Validate that the collection_name field is within the maximum length.

        Parameters:
            value (str): The collection_name string from the request.

        Returns:
            str: The validated collection_name string.

        Raises:
            ValueError: If the collection_name exceeds 3 characters.
        """
        if len(value) > 3:
            raise ValueError("collection_name must be max 3 chars")
        return value

    @field_validator("selected_text")
    @classmethod
    def validate_selected_text(cls, value: str) -> str:
        """
        Validate that the selected_text field is not empty after whitespace trimming.

        Parameters:
            value (str): The selected_text string from the request.

        Returns:
            str: Trimmed query string.

        Raises:
            ValueError: If the selected_text is empty after stripping whitespace.
        """
        value = value.strip()
        if not value:
            logger.error("selected text cannot be empty")
            raise ValueError("selected text cannot be empty")
        return value

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """
        Validate that the query field is not empty after whitespace trimming.

        Parameters:
            value (str): The query string from the request.

        Returns:
            str: Trimmed query string.

        Raises:
            ValueError: If the query is empty after stripping whitespace.
        """
        value = value.strip()
        if not value:
            logger.error("query cannot be empty")
            raise ValueError("query cannot be empty")
        return value
