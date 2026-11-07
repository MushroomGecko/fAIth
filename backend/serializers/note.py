import logging
from uuid import UUID

from pydantic import BaseModel, field_validator

from fAIth.function_globals import remove_newlines_whitespace

# Set up logging
logger = logging.getLogger(__name__)


class NoteInputSerializer(BaseModel):
    """
    Validates and deserializes note API requests, for both notes about selected verses and general notes.

    Ensures required fields are present and properly formatted before processing.

    Fields:
        collection_name (str): Name of the collection the note belongs to (max 3 chars).
        selected_text (str): The selected text from the user. Empty for a general note about the chapter.
        verses_text (str): The verses text from the user. Empty for a general note about the chapter.
        book (str): The book from the user.
        chapter (str): The chapter from the user.
        note (str): User's note (required, non-empty after strip).
    """

    collection_name: str
    selected_text: str = ""
    verses_text: str = ""
    book: str
    chapter: str
    note: str

    @field_validator("selected_text")
    @classmethod
    def validate_selected_text(cls, value: str) -> str:
        """
        Clean the selected_text field. It may be empty, for a general note about the chapter.

        Parameters:
            value (str): The selected_text string from the request.

        Returns:
            str: Cleaned selected text, or an empty string for a general note.
        """
        return remove_newlines_whitespace(value)

    @field_validator("verses_text")
    @classmethod
    def validate_verses_text(cls, value: str) -> str:
        """
        Trim the verses_text field. It may be empty, for a general note about the chapter.

        Parameters:
            value (str): The verses_text string from the request.

        Returns:
            str: Trimmed verses_text string, or an empty string for a general note.
        """
        return value.strip()

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

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        """
        Validate that the note field is not empty after whitespace trimming.

        Parameters:
            value (str): The note string from the request.

        Returns:
            str: Trimmed note string.

        Raises:
            ValueError: If the note is empty after stripping whitespace.
        """
        value = value.strip()
        if not value:
            logger.error("note cannot be empty")
            raise ValueError("note cannot be empty")
        return value


class UpdateNoteInputSerializer(BaseModel):
    """
    Validates and deserializes update note API requests.

    Fields:
        note_id (UUID): The ID of the note to update.
        note (str): The new note text (required, non-empty after strip).
    """

    note_id: UUID
    note: str

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        """
        Validate that the note field is not empty after whitespace trimming.

        Parameters:
            value (str): The note string from the request.

        Returns:
            str: Trimmed note string.

        Raises:
            ValueError: If the note is empty after stripping whitespace.
        """
        value = value.strip()
        if not value:
            logger.error("note cannot be empty")
            raise ValueError("note cannot be empty")
        return value


class DeleteNoteInputSerializer(BaseModel):
    """
    Validates and deserializes delete note API requests.

    Fields:
        note_id (UUID): The ID of the note to delete.
    """

    note_id: UUID


class ListNotesInputSerializer(BaseModel):
    """
    Validates and deserializes list notes API requests.

    Ensures required fields are present and properly formatted before processing.

    Fields:
        collection_name (str): Name of the collection the notes belong to (max 3 chars).
        book (str): The book from the user.
        chapter (str): The chapter from the user.
    """

    collection_name: str
    book: str
    chapter: str

    @field_validator("book")
    @classmethod
    def validate_list_book(cls, value: str) -> str:
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
    def validate_list_chapter(cls, value: str) -> str:
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
    def validate_list_collection_name(cls, value: str) -> str:
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
