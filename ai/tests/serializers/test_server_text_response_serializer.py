"""Tests for the ServerTextResponseSerializer."""

import pytest
from pydantic import ValidationError

from ai.serializers.server_text_response import ServerTextResponseSerializer


class TestServerTextResponseSerializer:
    """Tests for the ServerTextResponseSerializer."""

    def test_valid_response_content(self):
        """A non-empty string should validate successfully."""
        serializer = ServerTextResponseSerializer(response_content="<html>Response</html>")

        assert serializer.response_content == "<html>Response</html>"

    def test_empty_string_response_content_allowed(self):
        """Empty strings are permitted since no non-empty validator is defined."""
        serializer = ServerTextResponseSerializer(response_content="")

        assert serializer.response_content == ""

    def test_whitespace_response_content_allowed(self):
        """Whitespace-only strings are permitted since no trimming validator is defined."""
        serializer = ServerTextResponseSerializer(response_content="   \n\t  ")

        assert serializer.response_content == "   \n\t  "

    def test_missing_response_content_raises(self):
        """Omitting the required response_content field should raise ValidationError."""
        with pytest.raises(ValidationError):
            ServerTextResponseSerializer()  # type: ignore[call-arg]

    def test_non_string_response_content_raises(self):
        """A non-string response_content should raise ValidationError."""
        with pytest.raises(ValidationError):
            ServerTextResponseSerializer(response_content=123)  # type: ignore[arg-type]
