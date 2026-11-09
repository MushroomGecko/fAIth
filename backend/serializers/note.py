import json
import logging
import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from fAIth.function_globals import remove_newlines_whitespace

# Set up logging
logger = logging.getLogger(__name__)

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def validate_hex_color(value: str | None) -> str | None:
    """
    Validate a highlight color. An empty value means there is no highlight.

    Parameters:
        value (str | None): The highlight color from the request, e.g. "#ffff00".

    Returns:
        str | None: The color in uppercase (e.g. "#FFFF00"), or None if there is no highlight.

    Raises:
        ValueError: If the value is not a hex color like #RRGGBB.
    """
    if value is None or value.strip() == "":
        return None
    value = value.strip()
    if not HEX_COLOR_PATTERN.match(value):
        logger.error("highlight_color must be a hex color like #FFFF00")
        raise ValueError("highlight_color must be a hex color like #FFFF00")
    return value.upper()


class NoteInputSerializer(BaseModel):
    """
    Validates and deserializes note API requests, for both notes about selected verses and general notes.

    Ensures required fields are present and properly formatted before processing.

    Fields:
        collection_name (str): Name of the collection the note belongs to (max 3 chars).
        selected_html (str): The selected verse HTML from the user. Empty for a general note about the chapter.
        verses_text (str): The verses text from the user. Empty for a general note about the chapter.
        book (str): The book from the user.
        chapter (str): The chapter from the user.
        note (str): User's note (required, non-empty after strip).
    """

    collection_name: str
    selected_html: str = ""
    verses_text: str = ""
    book: str
    chapter: str
    note: str
    highlight_coordinates: dict[str, dict[str, int]] = {}
    highlight_color: str | None = None

    @field_validator("highlight_coordinates", mode="before")
    @classmethod
    def parse_highlight_coordinates(cls, value: Any) -> Any:
        """
        Parse highlight_coordinates from a JSON string (form posts) and treat blank input as no highlight.

        Parameters:
            value (Any): The highlight_coordinates value from the request.

        Returns:
            Any: A dict, or an empty dict if there is no highlight.

        Raises:
            ValueError: If the string is not valid JSON.
        """
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return {}
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as error:
                logger.error("highlight_coordinates must be valid JSON")
                raise ValueError("highlight_coordinates must be valid JSON") from error
        return value

    @field_validator("highlight_coordinates")
    @classmethod
    def validate_highlight_coordinates(cls, value: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
        """
        Validate that each verse key is a positive verse number and each value has exactly "beginning" and "end"
        as non-negative integers, with beginning before end.

        Parameters:
            value (dict[str, dict[str, int]]): The highlight coordinates, keyed by verse number.

        Returns:
            dict[str, dict[str, int]]: The validated highlight coordinates.

        Raises:
            ValueError: If a verse key or offset is invalid.
        """
        for verse_number, offsets in value.items():
            if not verse_number.isdigit() or int(verse_number) < 1:
                logger.error("highlight_coordinates keys must be positive verse numbers")
                raise ValueError("highlight_coordinates keys must be positive verse numbers")
            if set(offsets.keys()) != {"beginning", "end"}:
                logger.error("highlight_coordinates values must have exactly 'beginning' and 'end' keys")
                raise ValueError("highlight_coordinates values must have exactly 'beginning' and 'end' keys")
            if offsets["beginning"] < 0 or offsets["end"] <= offsets["beginning"]:
                logger.error("highlight 'beginning' must be non-negative and less than 'end'")
                raise ValueError("highlight 'beginning' must be non-negative and less than 'end'")
        return value

    @field_validator("highlight_color")
    @classmethod
    def validate_highlight_color(cls, value: str | None) -> str | None:
        """
        Validate the highlight_color field. It may be empty, for a note with no highlight.

        Parameters:
            value (str | None): The highlight_color string from the request.

        Returns:
            str | None: The uppercase hex color, or None if there is no highlight.
        """
        return validate_hex_color(value)

    @model_validator(mode="after")
    def validate_highlight_fields_together(self) -> "NoteInputSerializer":
        """
        Ensure highlight_color and highlight_coordinates are either both set or both empty.

        Returns:
            NoteInputSerializer: The validated serializer.

        Raises:
            ValueError: If only one of the highlight fields is set.
        """
        has_coordinates = bool(self.highlight_coordinates)
        has_color = self.highlight_color is not None
        if has_coordinates != has_color:
            logger.error("highlight_color and highlight_coordinates must both be set or both be empty")
            raise ValueError("highlight_color and highlight_coordinates must both be set or both be empty")
        return self

    @field_validator("selected_html")
    @classmethod
    def validate_selected_html(cls, value: str) -> str:
        """
        Clean the selected_html field. It may be empty, for a general note about the chapter.

        Parameters:
            value (str): The selected_html string from the request.

        Returns:
            str: Cleaned selected HTML, or an empty string for a general note.
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
    highlight_color: str | None = None

    @field_validator("highlight_color")
    @classmethod
    def validate_update_highlight_color(cls, value: str | None) -> str | None:
        """
        Validate the highlight_color field. Updates only change the color, never the coordinates.

        Parameters:
            value (str | None): The highlight_color string from the request.

        Returns:
            str | None: The uppercase hex color, or None if there is no highlight.
        """
        return validate_hex_color(value)

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
