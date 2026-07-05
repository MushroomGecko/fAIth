"""Tests for the devotional_chapter API endpoint."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from django.http import HttpRequest
from django.test import SimpleTestCase

from ai.views.devotional_chapter import devotional_chapter

DEFAULT_ALL_VERSES = {
    "bsb": {
        "Genesis": {
            1: {
                "1": "In the beginning God created the heavens and the earth.",
                "2": "Now the earth was formless and void, and darkness was over the surface of the deep. And the Spirit of God was hovering over the surface of the waters.",
                "3": 'And God said, "Let there be light," and there was light.',
                "4": "And God saw that the light was good, and He separated the light from the darkness.",
                "5": 'God called the light "day," and the darkness He called "night." And there was evening, and there was morning—the first day.',
            }
        }
    }
}


class TestDevotionalChapterView(SimpleTestCase):
    """Tests for the devotional_chapter API endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_path = Path("ai", "llm", "prompts", "devotional_chapter")

    def _call_devotional_chapter(self, request, payload):
        """Helper to call async devotional_chapter function."""
        return asyncio.run(devotional_chapter(request, payload))

    def _build_request(self):
        """Build a request with the required state."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "completions_obj": AsyncMock(),
        }
        return request

    def _build_payload(self, book="Genesis", chapter="1", collection_name="bsb"):
        """Build a mock payload matching DevotionalChapterInputSerializer fields."""
        payload = MagicMock()
        payload.book = book
        payload.chapter = chapter
        payload.collection_name = collection_name
        return payload

    def test_devotional_chapter_success(self):
        """Test successful devotional_chapter endpoint with valid payload."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch("ai.views.devotional_chapter.ALL_VERSES", DEFAULT_ALL_VERSES),
        ):
            request.state["completions_obj"].completions = AsyncMock(
                return_value="As you sit with Genesis 1 today, let the opening words settle over your heart."
            )

            async def mock_read(path):
                if "system.md" in str(path):
                    return "You are a devotional writer assistant."
                elif "user.md" in str(path):
                    return "Write a devotional for {book} Chapter {chapter} from {collection_name}:\n{verses}"
                return ""

            mock_read_file.side_effect = mock_read
            mock_clean.return_value = (
                "<p>As you sit with Genesis 1 today, let the opening words settle over your heart.</p>"
            )
            mock_render.return_value = "<html>Devotional</html>"

            response = self._call_devotional_chapter(request, payload)

            # Verify successful response
            assert response.status_code == 200
            assert "text/html" in response["content-type"]
            assert b"Devotional" in response.content

            # Verify LLM completions was called
            request.state["completions_obj"].completions.assert_called_once()

    def test_devotional_chapter_calls_llm_completions(self):
        """Test that devotional_chapter calls the LLM completions service."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch("ai.views.devotional_chapter.ALL_VERSES", DEFAULT_ALL_VERSES),
        ):
            request.state["completions_obj"].completions = AsyncMock(return_value="Creation devotional")

            async def mock_read(path):
                if "system.md" in str(path):
                    return "You are a devotional writer assistant."
                elif "user.md" in str(path):
                    return "Write a devotional for {book} Chapter {chapter} from {collection_name}:\n{verses}"
                return ""

            mock_read_file.side_effect = mock_read
            mock_clean.return_value = "<p>Creation devotional</p>"
            mock_render.return_value = "Rendered template"

            _ = self._call_devotional_chapter(request, payload)

            # Verify LLM completions was called with proper prompts
            request.state["completions_obj"].completions.assert_called_once()
            call_args = request.state["completions_obj"].completions.call_args
            # First arg is system_prompt, second is user_prompt
            assert call_args[0][0] == "You are a devotional writer assistant."  # system prompt
            assert "Genesis" in call_args[0][1]  # user prompt with book
            assert "1" in call_args[0][1]  # user prompt with chapter
            assert "bsb" in call_args[0][1]  # user prompt with collection_name

    def test_devotional_chapter_loads_correct_prompt_files(self):
        """Test that devotional_chapter loads prompts from correct file paths."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch("ai.views.devotional_chapter.ALL_VERSES", DEFAULT_ALL_VERSES),
        ):
            request.state["completions_obj"].completions = AsyncMock(return_value="Devotional")

            async def mock_read(path):
                return "Devotional prompt"

            mock_read_file.side_effect = mock_read
            mock_clean.return_value = "<p>Devotional</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_devotional_chapter(request, payload)

            # Verify both system and user prompts were loaded
            assert mock_read_file.call_count == 2
            call_paths = [call[0][0] for call in mock_read_file.call_args_list]
            path_strings = [str(p) for p in call_paths]
            assert any("system.md" in p for p in path_strings)
            assert any("user.md" in p for p in path_strings)

    def test_devotional_chapter_renders_template(self):
        """Test that devotional_chapter renders the response template."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch("ai.views.devotional_chapter.ALL_VERSES", DEFAULT_ALL_VERSES),
        ):
            request.state["completions_obj"].completions = AsyncMock(return_value="Devotional")

            async def mock_read(path):
                return "Devotional prompt"

            mock_read_file.side_effect = mock_read
            mock_clean.return_value = "<p>Devotional</p>"
            mock_render.return_value = "<html><body>Response</body></html>"

            _ = self._call_devotional_chapter(request, payload)

            # Verify template rendering
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == "partials/text.html"
            assert call_args[0][1]["response_content"] is not None

    def test_devotional_chapter_converts_chapter_to_int(self):
        """Test that devotional_chapter converts the chapter string to an integer for ALL_VERSES lookup.

        ALL_VERSES is keyed by int chapter numbers. If the string-to-int conversion were removed,
        the lookup would raise a KeyError and completions would never be called.
        """
        request = self._build_request()
        payload = self._build_payload(chapter="5")  # string — view must convert to int 5 to hit the key below

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch(
                "ai.views.devotional_chapter.ALL_VERSES",
                {
                    "bsb": {
                        "Genesis": {
                            5: {  # int key — only reachable via int("5")
                                "1": "This is the book of the generations of Adam.",
                                "2": "Male and female He created them.",
                            }
                        }
                    }
                },
            ),
        ):
            request.state["completions_obj"].completions = AsyncMock(return_value="Devotional")

            async def mock_read(path):
                if "user.md" in str(path):
                    return "Write a devotional for {book} Chapter {chapter} from {collection_name}:\n{verses}"
                return "System prompt"

            mock_read_file.side_effect = mock_read
            mock_clean.return_value = "<p>Devotional</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_devotional_chapter(request, payload)

            # If int() conversion didn't happen, ALL_VERSES["bsb"]["Genesis"]["5"] would
            # raise KeyError and completions would never be reached.
            request.state["completions_obj"].completions.assert_called_once()
            call_args = request.state["completions_obj"].completions.call_args
            user_prompt = call_args[0][1]
            assert "Genesis" in user_prompt
            assert "5" in user_prompt

    def test_devotional_chapter_stringifies_verses(self):
        """Test that devotional_chapter properly stringifies verses with newlines."""
        request = self._build_request()
        payload = self._build_payload()

        verses_dict = {
            "1": "In the beginning God created the heavens and the earth.",
            "2": "Now the earth was formless and void, and darkness was over the surface of the deep. And the Spirit of God was hovering over the surface of the waters.",
            "3": 'And God said, "Let there be light," and there was light.',
        }

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch("ai.views.devotional_chapter.ALL_VERSES", {"bsb": {"Genesis": {1: verses_dict}}}),
        ):
            request.state["completions_obj"].completions = AsyncMock(return_value="Devotional")

            async def mock_read(path):
                if "user.md" in str(path):
                    return "Write a devotional for {book} Chapter {chapter} from {collection_name}:\n{verses}"
                return "System prompt"

            mock_read_file.side_effect = mock_read
            mock_clean.return_value = "<p>Devotional</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_devotional_chapter(request, payload)

            # Verify the user prompt contains stringified verses joined with newlines
            call_args = request.state["completions_obj"].completions.call_args
            user_prompt = call_args[0][1]

            # Should contain all three verses joined with newlines
            assert "In the beginning God created the heavens and the earth." in user_prompt
            assert (
                "Now the earth was formless and void, and darkness was over the surface of the deep. And the Spirit of God was hovering over the surface of the waters."
                in user_prompt
            )
            assert 'And God said, "Let there be light," and there was light.' in user_prompt

    def test_devotional_chapter_cleans_llm_output(self):
        """Test that devotional_chapter cleans LLM output."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch(
                "ai.views.devotional_chapter.ALL_VERSES",
                {"bsb": {"Genesis": {1: {"1": "In the beginning God created the heavens and the earth."}}}},
            ),
        ):
            raw_output = "**Creation** devotional\n\n- Light\n- Water"
            request.state["completions_obj"].completions = AsyncMock(return_value=raw_output)

            async def mock_read(path):
                return "Devotional prompt"

            mock_read_file.side_effect = mock_read

            cleaned_html = "<p><strong>Creation</strong> devotional</p><ul><li>Light</li><li>Water</li></ul>"
            mock_clean.return_value = cleaned_html
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_devotional_chapter(request, payload)

            # Verify clean_llm_output was called with the raw output
            mock_clean.assert_called_once_with(raw_output)

    def test_devotional_chapter_marks_response_as_safe(self):
        """Test that devotional_chapter marks HTML response as safe."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch(
                "ai.views.devotional_chapter.ALL_VERSES",
                {"bsb": {"Genesis": {1: {"1": "In the beginning God created the heavens and the earth."}}}},
            ),
            patch("ai.views.devotional_chapter.mark_safe") as mock_mark_safe,
        ):
            request.state["completions_obj"].completions = AsyncMock(return_value="Devotional")

            async def mock_read(path):
                return "Devotional prompt"

            mock_read_file.side_effect = mock_read

            cleaned_html = "<p>Devotional</p>"
            mock_clean.return_value = cleaned_html
            mock_mark_safe.return_value = cleaned_html
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_devotional_chapter(request, payload)

            # Verify mark_safe was called with cleaned HTML
            mock_mark_safe.assert_called_once_with(cleaned_html)

    def test_devotional_chapter_different_collections(self):
        """Test that collection_name is used as the key into ALL_VERSES.

        Each collection has distinct verse text; the test verifies that the correct
        collection's verses appear in the user prompt, confirming collection_name
        drives the lookup rather than defaulting to a fixed key.
        """
        collections = {
            "bsb": "BSB-specific verse text for Genesis one.",
            "niv": "NIV-specific verse text for Genesis one.",
            "kjv": "KJV-specific verse text for Genesis one.",
        }

        for collection, unique_verse in collections.items():
            with self.subTest(collection=collection):
                request = self._build_request()
                payload = self._build_payload(collection_name=collection)

                with (
                    patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
                    patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
                    patch("ai.views.devotional_chapter.render_to_string") as mock_render,
                    patch(
                        "ai.views.devotional_chapter.ALL_VERSES", {collection: {"Genesis": {1: {"1": unique_verse}}}}
                    ),
                ):
                    request.state["completions_obj"].completions = AsyncMock(return_value="Devotional")

                    async def mock_read(path):
                        if "user.md" in str(path):
                            return "Write a devotional for {book} Chapter {chapter} from {collection_name}:\n{verses}"
                        return "System prompt"

                    mock_read_file.side_effect = mock_read
                    mock_clean.return_value = "<p>Devotional</p>"
                    mock_render.return_value = "<html>Response</html>"

                    _ = self._call_devotional_chapter(request, payload)

                    # Verify the verse text unique to this collection made it into the prompt,
                    # confirming collection_name was used as the ALL_VERSES key.
                    call_args = request.state["completions_obj"].completions.call_args
                    user_prompt = call_args[0][1]
                    assert unique_verse in user_prompt
                    # Each format placeholder is interpolated into the user prompt template,
                    # so its value must appear verbatim — guards against dropping any of them
                    # from the format call.
                    assert collection in user_prompt  # collection_name
                    assert "Genesis" in user_prompt  # book
                    assert "1" in user_prompt  # chapter

    def _assert_500_error(self, response, message_substring):
        """Assert a 500 HTML error response containing the given message."""
        assert response.status_code == 500
        assert "text/html" in response["content-type"]
        assert message_substring.encode() in response.content

    def test_devotional_chapter_error_locating_verses(self):
        """Test that a missing book/chapter/collection in ALL_VERSES returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload(book="Missing", chapter="999")

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch("ai.views.devotional_chapter.ALL_VERSES", DEFAULT_ALL_VERSES),
        ):
            request.state["completions_obj"].completions = AsyncMock(return_value="Devotional")

            async def mock_read(path):
                return "Devotional prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_devotional_chapter(request, payload)

            self._assert_500_error(response, "Error locating verses")
            request.state["completions_obj"].completions.assert_not_called()
            mock_render.assert_not_called()

    def test_devotional_chapter_error_formatting_user_prompt(self):
        """Test that a failure loading/formatting prompts returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch("ai.views.devotional_chapter.ALL_VERSES", DEFAULT_ALL_VERSES),
        ):
            request.state["completions_obj"].completions = AsyncMock(return_value="Devotional")
            # async_read_file raises before any prompt formatting can happen
            mock_read_file.side_effect = FileNotFoundError("missing system.md")

            response = self._call_devotional_chapter(request, payload)

            self._assert_500_error(response, "Error formatting user prompt")
            mock_render.assert_not_called()

    def test_devotional_chapter_error_stripping_whitespace(self):
        """Test that a failure stripping prompts returns a 500 error.

        system_prompt is a non-string so .strip() raises AttributeError after the
        formatting block succeeds.
        """
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch("ai.views.devotional_chapter.ALL_VERSES", DEFAULT_ALL_VERSES),
        ):
            request.state["completions_obj"].completions = AsyncMock(return_value="Devotional")

            async def mock_read(path):
                if "system.md" in str(path):
                    return 123  # non-string: .strip() will raise
                elif "user.md" in str(path):
                    return "Write a devotional for {book} Chapter {chapter} from {collection_name}:\n{verses}"
                return ""

            mock_read_file.side_effect = mock_read

            response = self._call_devotional_chapter(request, payload)

            self._assert_500_error(response, "Error stripping whitespace")
            mock_render.assert_not_called()

    def test_devotional_chapter_error_generating_llm_response(self):
        """Test that an LLM completions failure returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch("ai.views.devotional_chapter.ALL_VERSES", DEFAULT_ALL_VERSES),
        ):
            request.state["completions_obj"].completions = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

            async def mock_read(path):
                return "Devotional prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_devotional_chapter(request, payload)

            self._assert_500_error(response, "Error generating LLM response")
            mock_clean.assert_not_called()
            mock_render.assert_not_called()

    def test_devotional_chapter_error_cleaning_llm_output(self):
        """Test that a failure cleaning LLM output returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch("ai.views.devotional_chapter.ALL_VERSES", DEFAULT_ALL_VERSES),
        ):
            request.state["completions_obj"].completions = AsyncMock(return_value="raw markdown")
            mock_clean.side_effect = RuntimeError("cleaner failed")

            async def mock_read(path):
                return "Devotional prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_devotional_chapter(request, payload)

            self._assert_500_error(response, "Error cleaning LLM output")
            mock_render.assert_not_called()

    def test_devotional_chapter_error_rendering_template(self):
        """Test that a template rendering failure returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch("ai.views.devotional_chapter.ALL_VERSES", DEFAULT_ALL_VERSES),
            patch("ai.views.devotional_chapter.ServerTextResponseSerializer") as mock_serializer,
        ):
            request.state["completions_obj"].completions = AsyncMock(return_value="raw markdown")
            mock_clean.return_value = "<p>Devotional</p>"
            mock_render.side_effect = RuntimeError("template missing")

            async def mock_read(path):
                return "Devotional prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_devotional_chapter(request, payload)

            self._assert_500_error(response, "Error rendering template")
            mock_serializer.assert_not_called()

    def test_devotional_chapter_error_validating_output(self):
        """Test that a serializer validation failure returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.devotional_chapter.async_read_file") as mock_read_file,
            patch("ai.views.devotional_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.devotional_chapter.render_to_string") as mock_render,
            patch("ai.views.devotional_chapter.ALL_VERSES", DEFAULT_ALL_VERSES),
            patch("ai.views.devotional_chapter.ServerTextResponseSerializer") as mock_serializer,
        ):
            request.state["completions_obj"].completions = AsyncMock(return_value="raw markdown")
            mock_clean.return_value = "<p>Devotional</p>"
            mock_render.return_value = "<html>Response</html>"
            mock_serializer.side_effect = ValueError("invalid response_content")

            async def mock_read(path):
                return "Devotional prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_devotional_chapter(request, payload)

            self._assert_500_error(response, "Error validating output")
