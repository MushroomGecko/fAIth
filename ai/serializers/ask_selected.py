import logging

from pydantic import BaseModel, field_validator

from ai.utils import remove_newlines_whitespace

# Set up logging
logger = logging.getLogger(__name__)


class AskSelectedInputSerializer(BaseModel):
    """
    Validates and deserializes ask selected API requests.

    Ensures required fields are present and properly formatted before processing.

    Fields:
        collection_name (str): Name of the Milvus collection to search (max 3 chars).
        selected_text (str): The selected text from the user.
        verses_text (str): The verses text from the user.
        book (str): The book from the user.
        chapter (str): The chapter from the user.
        query (str): User's question or search query (required, non-empty after strip).
    """

    collection_name: str
    selected_text: str
    verses_text: str
    book: str
    chapter: str
    query: str

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
        value = remove_newlines_whitespace(value)
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
