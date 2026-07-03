"""Tests for the summarize_chapter API endpoint."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from django.http import HttpRequest
from django.test import SimpleTestCase

from ai.views.summarize_chapter import summarize_chapter


class TestSummarizeChapterView(SimpleTestCase):
    """Tests for the summarize_chapter API endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_path = Path("ai", "llm", "prompts", "summarize_chapter")

    def _call_summarize_chapter(self, request, payload):
        """Helper to call async summarize_chapter function."""
        return asyncio.run(summarize_chapter(request, payload))

    def test_summarize_chapter_success(self):
        """Test successful summarize_chapter endpoint with valid payload."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.book = "Genesis"
        payload.chapter = "1"
        payload.collection_name = "bsb"

        with patch("ai.views.summarize_chapter.async_read_file") as mock_read_file, patch("ai.views.summarize_chapter.clean_llm_output") as mock_clean, patch("ai.views.summarize_chapter.render_to_string") as mock_render, patch("ai.views.summarize_chapter.ALL_VERSES", {"bsb": {"Genesis": {1: {"1": "In the beginning God created the heavens and the earth.", "2": "Now the earth was formless and void, and darkness was over the surface of the deep. And the Spirit of God was hovering over the surface of the waters.", "3": 'And God said, "Let there be light," and there was light.', "4": "And God saw that the light was good, and He separated the light from the darkness.", "5": 'God called the light "day," and the darkness He called "night." And there was evening, and there was morning—the first day.'}}}}):
            request.state["completions_obj"].completions = AsyncMock(return_value="In the beginning, God created the heavens and the earth.")

            async def mock_read(path):
                if "system.md" in str(path):
                    return "You are a Bible summarization assistant."
                elif "user.md" in str(path):
                    return "Summarize {book} Chapter {chapter}:\n{verses}"
                return ""

            mock_read_file.side_effect = mock_read
            mock_clean.return_value = "<p>In the beginning, God created the heavens and the earth.</p>"
            mock_render.return_value = "<html>Summary</html>"

            response = self._call_summarize_chapter(request, payload)

            # Verify successful response
            assert response.status_code == 200
            assert "text/html" in response["content-type"]
            assert b"Summary" in response.content

            # Verify LLM completions was called
            request.state["completions_obj"].completions.assert_called_once()

    def test_summarize_chapter_calls_llm_completions(self):
        """Test that summarize_chapter calls the LLM completions service."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.book = "Genesis"
        payload.chapter = "1"
        payload.collection_name = "bsb"

        with patch("ai.views.summarize_chapter.async_read_file") as mock_read_file, patch("ai.views.summarize_chapter.clean_llm_output") as mock_clean, patch("ai.views.summarize_chapter.render_to_string") as mock_render, patch("ai.views.summarize_chapter.ALL_VERSES", {"bsb": {"Genesis": {1: {"1": "In the beginning God created the heavens and the earth.", "2": "Now the earth was formless and void, and darkness was over the surface of the deep. And the Spirit of God was hovering over the surface of the waters.", "3": 'And God said, "Let there be light," and there was light.', "4": "And God saw that the light was good, and He separated the light from the darkness.", "5": 'God called the light "day," and the darkness He called "night." And there was evening, and there was morning—the first day.'}}}}):
            request.state["completions_obj"].completions = AsyncMock(return_value="Creation summary")

            async def mock_read(path):
                if "system.md" in str(path):
                    return "You are a Bible summarization assistant."
                elif "user.md" in str(path):
                    return "Summarize {book} Chapter {chapter}:\n{verses}"
                return ""

            mock_read_file.side_effect = mock_read
            mock_clean.return_value = "<p>Creation summary</p>"
            mock_render.return_value = "Rendered template"

            _ = self._call_summarize_chapter(request, payload)

            # Verify LLM completions was called with proper prompts
            request.state["completions_obj"].completions.assert_called_once()
            call_args = request.state["completions_obj"].completions.call_args
            # First arg is system_prompt, second is user_prompt
            assert call_args[0][0] == "You are a Bible summarization assistant."  # system prompt
            assert "Genesis" in call_args[0][1]  # user prompt with book
            assert "1" in call_args[0][1]  # user prompt with chapter

    def test_summarize_chapter_loads_correct_prompt_files(self):
        """Test that summarize_chapter loads prompts from correct file paths."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.book = "Genesis"
        payload.chapter = "1"
        payload.collection_name = "bsb"

        with patch("ai.views.summarize_chapter.async_read_file") as mock_read_file, patch("ai.views.summarize_chapter.clean_llm_output") as mock_clean, patch("ai.views.summarize_chapter.render_to_string") as mock_render, patch("ai.views.summarize_chapter.ALL_VERSES", {"bsb": {"Genesis": {1: {"1": "In the beginning God created the heavens and the earth.", "2": "Now the earth was formless and void, and darkness was over the surface of the deep. And the Spirit of God was hovering over the surface of the waters."}}}}):
            request.state["completions_obj"].completions = AsyncMock(return_value="Summary")

            async def mock_read(path):
                return "Bible prompt"

            mock_read_file.side_effect = mock_read
            mock_clean.return_value = "<p>Summary</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_summarize_chapter(request, payload)

            # Verify both system and user prompts were loaded
            assert mock_read_file.call_count == 2
            call_paths = [call[0][0] for call in mock_read_file.call_args_list]
            path_strings = [str(p) for p in call_paths]
            assert any("system.md" in p for p in path_strings)
            assert any("user.md" in p for p in path_strings)

    def test_summarize_chapter_renders_template(self):
        """Test that summarize_chapter renders the response template."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.book = "Genesis"
        payload.chapter = "1"
        payload.collection_name = "bsb"

        with patch("ai.views.summarize_chapter.async_read_file") as mock_read_file, patch("ai.views.summarize_chapter.clean_llm_output") as mock_clean, patch("ai.views.summarize_chapter.render_to_string") as mock_render, patch("ai.views.summarize_chapter.ALL_VERSES", {"bsb": {"Genesis": {1: {"1": "In the beginning God created the heavens and the earth.", "2": "Now the earth was formless and void, and darkness was over the surface of the deep. And the Spirit of God was hovering over the surface of the waters."}}}}):
            request.state["completions_obj"].completions = AsyncMock(return_value="Summary")

            async def mock_read(path):
                return "Bible prompt"

            mock_read_file.side_effect = mock_read
            mock_clean.return_value = "<p>Summary</p>"
            mock_render.return_value = "<html><body>Response</body></html>"

            _ = self._call_summarize_chapter(request, payload)

            # Verify template rendering
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == "partials/text.html"
            assert call_args[0][1]["response_content"] is not None

    def test_summarize_chapter_converts_chapter_to_int(self):
        """Test that summarize_chapter converts the chapter string to an integer for ALL_VERSES lookup.

        ALL_VERSES is keyed by int chapter numbers. If the string-to-int conversion were removed,
        the lookup would raise a KeyError and completions would never be called.
        """
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.book = "Genesis"
        payload.chapter = "5"  # string — view must convert to int 5 to hit the key below
        payload.collection_name = "bsb"

        with (
            patch("ai.views.summarize_chapter.async_read_file") as mock_read_file,
            patch("ai.views.summarize_chapter.clean_llm_output") as mock_clean,
            patch("ai.views.summarize_chapter.render_to_string") as mock_render,
            patch(
                "ai.views.summarize_chapter.ALL_VERSES",
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
            request.state["completions_obj"].completions = AsyncMock(return_value="Summary")

            async def mock_read(path):
                if "user.md" in str(path):
                    return "Summarize {book} Chapter {chapter}:\n{verses}"
                return "System prompt"

            mock_read_file.side_effect = mock_read
            mock_clean.return_value = "<p>Summary</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_summarize_chapter(request, payload)

            # If int() conversion didn't happen, ALL_VERSES["bsb"]["Genesis"]["5"] would
            # raise KeyError and completions would never be reached.
            request.state["completions_obj"].completions.assert_called_once()
            call_args = request.state["completions_obj"].completions.call_args
            user_prompt = call_args[0][1]
            assert "Genesis" in user_prompt
            assert "5" in user_prompt

    def test_summarize_chapter_stringifies_verses(self):
        """Test that summarize_chapter properly stringifies verses with newlines."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.book = "Genesis"
        payload.chapter = "1"
        payload.collection_name = "bsb"

        verses_dict = {"1": "In the beginning God created the heavens and the earth.", "2": "Now the earth was formless and void, and darkness was over the surface of the deep. And the Spirit of God was hovering over the surface of the waters.", "3": 'And God said, "Let there be light," and there was light.'}

        with patch("ai.views.summarize_chapter.async_read_file") as mock_read_file, patch("ai.views.summarize_chapter.clean_llm_output") as mock_clean, patch("ai.views.summarize_chapter.render_to_string") as mock_render, patch("ai.views.summarize_chapter.ALL_VERSES", {"bsb": {"Genesis": {1: verses_dict}}}):
            request.state["completions_obj"].completions = AsyncMock(return_value="Summary")

            async def mock_read(path):
                if "user.md" in str(path):
                    return "Summarize {book} Chapter {chapter}:\n{verses}"
                return "System prompt"

            mock_read_file.side_effect = mock_read
            mock_clean.return_value = "<p>Summary</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_summarize_chapter(request, payload)

            # Verify the user prompt contains stringified verses joined with newlines
            call_args = request.state["completions_obj"].completions.call_args
            user_prompt = call_args[0][1]

            # Should contain all three verses joined with newlines
            assert "In the beginning God created the heavens and the earth." in user_prompt
            assert "Now the earth was formless and void, and darkness was over the surface of the deep. And the Spirit of God was hovering over the surface of the waters." in user_prompt
            assert 'And God said, "Let there be light," and there was light.' in user_prompt

    def test_summarize_chapter_cleans_llm_output(self):
        """Test that summarize_chapter cleans LLM output."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.book = "Genesis"
        payload.chapter = "1"
        payload.collection_name = "bsb"

        with patch("ai.views.summarize_chapter.async_read_file") as mock_read_file, patch("ai.views.summarize_chapter.clean_llm_output") as mock_clean, patch("ai.views.summarize_chapter.render_to_string") as mock_render, patch("ai.views.summarize_chapter.ALL_VERSES", {"bsb": {"Genesis": {1: {"1": "In the beginning God created the heavens and the earth."}}}}):
            raw_output = "**Creation** of the world\n\n- Light\n- Water"
            request.state["completions_obj"].completions = AsyncMock(return_value=raw_output)

            async def mock_read(path):
                return "Bible prompt"

            mock_read_file.side_effect = mock_read

            cleaned_html = "<p><strong>Creation</strong> of the world</p><ul><li>Light</li><li>Water</li></ul>"
            mock_clean.return_value = cleaned_html
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_summarize_chapter(request, payload)

            # Verify clean_llm_output was called with the raw output
            mock_clean.assert_called_once_with(raw_output)

    def test_summarize_chapter_marks_response_as_safe(self):
        """Test that summarize_chapter marks HTML response as safe."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.book = "Genesis"
        payload.chapter = "1"
        payload.collection_name = "bsb"

        with patch("ai.views.summarize_chapter.async_read_file") as mock_read_file, patch("ai.views.summarize_chapter.clean_llm_output") as mock_clean, patch("ai.views.summarize_chapter.render_to_string") as mock_render, patch("ai.views.summarize_chapter.ALL_VERSES", {"bsb": {"Genesis": {1: {"1": "In the beginning God created the heavens and the earth."}}}}), patch("ai.views.summarize_chapter.mark_safe") as mock_mark_safe:
            request.state["completions_obj"].completions = AsyncMock(return_value="Summary")

            async def mock_read(path):
                return "Bible prompt"

            mock_read_file.side_effect = mock_read

            cleaned_html = "<p>Summary</p>"
            mock_clean.return_value = cleaned_html
            mock_mark_safe.return_value = cleaned_html
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_summarize_chapter(request, payload)

            # Verify mark_safe was called with cleaned HTML
            mock_mark_safe.assert_called_once_with(cleaned_html)

    def test_summarize_chapter_different_collections(self):
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
                request = HttpRequest()
                request.method = "POST"
                request.state = {"completions_obj": AsyncMock()}

                payload = MagicMock()
                payload.book = "Genesis"
                payload.chapter = "1"
                payload.collection_name = collection

                with patch("ai.views.summarize_chapter.async_read_file") as mock_read_file, patch("ai.views.summarize_chapter.clean_llm_output") as mock_clean, patch("ai.views.summarize_chapter.render_to_string") as mock_render, patch("ai.views.summarize_chapter.ALL_VERSES", {collection: {"Genesis": {1: {"1": unique_verse}}}}):
                    request.state["completions_obj"].completions = AsyncMock(return_value="Summary")

                    async def mock_read(path):
                        if "user.md" in str(path):
                            return "Summarize {book} Chapter {chapter}:\n{verses}"
                        return "System prompt"

                    mock_read_file.side_effect = mock_read
                    mock_clean.return_value = "<p>Summary</p>"
                    mock_render.return_value = "<html>Response</html>"

                    _ = self._call_summarize_chapter(request, payload)

                    # Verify the verse text unique to this collection made it into the prompt,
                    # confirming collection_name was used as the ALL_VERSES key.
                    call_args = request.state["completions_obj"].completions.call_args
                    user_prompt = call_args[0][1]
                    assert unique_verse in user_prompt
