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
        verses_text (str): The verses text from the user to search an image for.
        book (str): The book from the user to search an image for.
        chapter (str): The chapter from the user to search an image for.
    """
    selected_text: str
    verses_text: str
    book: str
    chapter: str

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

    @field_validator("verses_text")
    @classmethod
    def validate_verses_text(cls, value: str) -> str:
        """
        Validate that the verses_text field is not empty after whitespace trimming.

        Parameters:
            value (str): The verses_text string from the request.

        Returns:
            str: Trimmed verses_text string.

        Raises:
            ValueError: If the verses_text is empty after stripping whitespace.
        """
        value = value.strip()
        if not value:
            logger.error("verses text cannot be empty")
            raise ValueError("verses text cannot be empty")
        return value

    @field_validator("book")
    @classmethod
    def validate_book(cls, value: str) -> str:
        """
        Validate that the book field is not empty after whitespace trimming.

        Parameters:
            value (str): The book string from the request.

        Returns:
            str: Trimmed book string.
            ValueError: If the book is empty after stripping whitespace.
        """
        value = value.strip()
        if not value:
            logger.error("book cannot be empty")
            raise ValueError("book cannot be empty")
        return value

    @field_validator("chapter")
    @classmethod
    def validate_chapter(cls, value: str) -> str:
        """
        Validate that the chapter field is not empty after whitespace trimming.

        Parameters:
            value (str): The chapter string from the request.

        Returns:
            str: Trimmed chapter string.
            ValueError: If the chapter is empty after stripping whitespace.
        """
        value = value.strip()
        if not value:
            logger.error("chapter cannot be empty")
            raise ValueError("chapter cannot be empty")
        return value