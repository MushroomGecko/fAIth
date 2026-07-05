import logging

from pydantic import BaseModel, field_validator

# Set up logging
logger = logging.getLogger(__name__)


class DevotionalChapterInputSerializer(BaseModel):
    """
    Validates and deserializes devotional chapter API requests.

    Ensures required fields are present and properly formatted before processing.

    Fields:
        book (str): Name of the book to generate a devotional for.
        chapter (str): Chapter to generate a devotional for.
        collection_name (str): Name of the Milvus collection to search (max 3 chars).
    """

    book: str
    chapter: str
    collection_name: str

    @field_validator("book")
    @classmethod
    def validate_book(cls, value: str) -> str:
        """
        Validate that the book field is not empty after whitespace trimming.

        Parameters:
            value (str): The book string from the request.

        Returns:
            str: Trimmed book string.

        Raises:
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

        Raises:
            ValueError: If the chapter is empty after stripping whitespace.
        """
        value = value.strip()
        if not value:
            logger.error("chapter cannot be empty")
            raise ValueError("chapter cannot be empty")
        return value

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
