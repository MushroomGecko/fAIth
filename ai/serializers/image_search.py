import logging

from pydantic import BaseModel, field_validator

# Set up logging
logger = logging.getLogger(__name__)


class ImageSearchInputSerializer(BaseModel):
    """
    Validates and deserializes image search API requests.

    Ensures required fields are present and properly formatted before processing.

    Fields:
        selected_text (str): The selected text from the user to search an image for.
    """
    selected_text: str

    @field_validator("selected_text")
    @classmethod
    def validate_selected_text(cls, value: str) -> str:
        """
        Validate that the selected_text field is not empty after whitespace trimming.

        Parameters:
            value (str): The selected_text string from the request.

        Returns:
            str: Trimmed selected_text string.

        Raises:
            ValueError: If the selected_text is empty after stripping whitespace.
        """
        value = value.strip()
        if not value:
            logger.error("selected text cannot be empty")
            raise ValueError("selected text cannot be empty")
        return value
