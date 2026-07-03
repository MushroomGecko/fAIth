"""Tests for the image_search API endpoint."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from django.http import HttpRequest
from django.test import SimpleTestCase

from ai.views.image_search import image_search


class TestImageSearchView(SimpleTestCase):
    """Tests for the image_search API endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_path = Path("ai", "llm", "prompts", "image_search")

    def _call_image_search(self, request, payload):
        """Helper to call async image_search function."""
        return asyncio.run(image_search(request, payload))

    def _build_request(self):
        """Build a request with the required state."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "completions_obj": AsyncMock(),
        }
        return request

    def _build_payload(self):
        """Build a mock payload matching ImageSearchInputSerializer fields."""
        payload = MagicMock()
        payload.selected_text = "For God so loved the world"
        payload.verses_text = "16) For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life."
        payload.book = "John"
        payload.chapter = "3"
        return payload

    def test_image_search_success(self):
        """Test successful image_search endpoint with valid payload."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render:
            request.state["completions_obj"].completions = AsyncMock(return_value="cross resurrection")
            mock_search.return_value = ["http://example.com/img1.jpg"]
            mock_render.return_value = "<html>Response</html>"

            async def mock_read(path):
                if "system.md" in str(path):
                    return "You are a helpful image search assistant."
                elif "user.md" in str(path):
                    return "Selected: {selected_text}\nVerses: {verses_text}\nBook: {book}\nChapter: {chapter}"
                return ""

            mock_read_file.side_effect = mock_read

            response = self._call_image_search(request, payload)

            # Verify successful response
            assert response.status_code == 200
            assert "text/html" in response["content-type"]
            assert b"Response" in response.content

    def test_image_search_calls_llm_completions(self):
        """Test that image_search calls the LLM completions service."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render:
            request.state["completions_obj"].completions = AsyncMock(return_value="cross resurrection")
            mock_search.return_value = ["http://example.com/img1.jpg"]
            mock_render.return_value = "<html>Response</html>"

            async def mock_read(path):
                if "system.md" in str(path):
                    return "You are a helpful image search assistant."
                elif "user.md" in str(path):
                    return "Selected: {selected_text}\nVerses: {verses_text}\nBook: {book}\nChapter: {chapter}"
                return ""

            mock_read_file.side_effect = mock_read

            _ = self._call_image_search(request, payload)

            # Verify LLM completions was called once with proper prompts
            request.state["completions_obj"].completions.assert_called_once()
            call_args = request.state["completions_obj"].completions.call_args
            # First arg is system_prompt, second is user_prompt, third is selected_text
            assert call_args[0][0] == "You are a helpful image search assistant."
            # All payload fields should be interpolated into the user prompt
            assert "For God so loved the world" in call_args[0][1]
            assert "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life." in call_args[0][1]
            assert "John" in call_args[0][1]
            assert "3" in call_args[0][1]
            assert call_args[0][2] == "For God so loved the world"

    def test_image_search_loads_correct_prompt_files(self):
        """Test that image_search loads prompts from correct file paths."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render:
            request.state["completions_obj"].completions = AsyncMock(return_value="cross resurrection")
            mock_search.return_value = ["http://example.com/img1.jpg"]
            mock_render.return_value = "<html>Response</html>"

            async def mock_read(path):
                return "Bible image search prompt"

            mock_read_file.side_effect = mock_read

            _ = self._call_image_search(request, payload)

            # Verify both system and user prompts were loaded
            assert mock_read_file.call_count == 2
            call_paths = [call[0][0] for call in mock_read_file.call_args_list]
            path_strings = [str(p) for p in call_paths]
            assert any("system.md" in p for p in path_strings)
            assert any("user.md" in p for p in path_strings)
            # Prompts should come from the image_search prompt directory
            assert all("image_search" in p for p in path_strings)

    def test_image_search_calls_search_for_images_with_llm_query(self):
        """Test that image_search passes the LLM-generated query to search_for_images."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render:
            request.state["completions_obj"].completions = AsyncMock(return_value="cross resurrection")
            mock_search.return_value = ["http://example.com/img1.jpg"]
            mock_render.return_value = "<html>Response</html>"

            async def mock_read(path):
                return "Bible image search prompt"

            mock_read_file.side_effect = mock_read

            _ = self._call_image_search(request, payload)

            # Verify search_for_images was called with the LLM-generated query
            mock_search.assert_awaited_once()
            call_args = mock_search.call_args
            assert call_args[0][0] == "cross resurrection"

    def test_image_search_uses_searxng_image_limit(self):
        """Test that image_search passes the configured SEARXNG_IMAGE_LIMIT."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render, patch("ai.views.image_search.SEARXNG_IMAGE_LIMIT", 7):
            request.state["completions_obj"].completions = AsyncMock(return_value="cross resurrection")
            mock_search.return_value = ["http://example.com/img1.jpg"]
            mock_render.return_value = "<html>Response</html>"

            async def mock_read(path):
                return "Bible image search prompt"

            mock_read_file.side_effect = mock_read

            _ = self._call_image_search(request, payload)

            # Verify search_for_images was called with the configured limit
            call_args = mock_search.call_args
            assert call_args[0][1] == 7

    def test_image_search_handles_empty_image_results(self):
        """Test that image_search handles empty image search results."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render:
            request.state["completions_obj"].completions = AsyncMock(return_value="cross resurrection")
            mock_search.return_value = []  # No images returned
            mock_render.return_value = "<html>Response</html>"

            async def mock_read(path):
                return "Bible image search prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_image_search(request, payload)

            assert response.status_code == 200
            mock_search.assert_awaited_once()
            # Template should still be rendered
            mock_render.assert_called_once()

    def test_image_search_builds_html_image_tags(self):
        """Test that image_search builds <img> tags for each returned URL."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render:
            request.state["completions_obj"].completions = AsyncMock(return_value="cross resurrection")
            mock_search.return_value = [
                "http://example.com/img1.jpg",
                "http://example.com/img2.jpg",
                "http://example.com/img3.jpg",
            ]
            mock_render.return_value = "<html>Response</html>"

            async def mock_read(path):
                return "Bible image search prompt"

            mock_read_file.side_effect = mock_read

            _ = self._call_image_search(request, payload)

            # Verify the response_content passed to the template contains all image URLs
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == "partials/text.html"
            context = call_args[0][1]
            response_content = context["response_content"]
            assert response_content is not None
            assert "http://example.com/img1.jpg" in response_content
            assert "http://example.com/img2.jpg" in response_content
            assert "http://example.com/img3.jpg" in response_content
            # Should contain <img> tags
            assert response_content.count("<img") == 3

    def test_image_search_strips_prompts(self):
        """Test that image_search strips leading/trailing whitespace from prompts."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render:
            request.state["completions_obj"].completions = AsyncMock(return_value="cross resurrection")
            mock_search.return_value = ["http://example.com/img1.jpg"]
            mock_render.return_value = "<html>Response</html>"

            async def mock_read(path):
                if "system.md" in str(path):
                    return "\n  System prompt with whitespace  \n"
                elif "user.md" in str(path):
                    return "\n  Selected: {selected_text}\nVerses: {verses_text}\nBook: {book}\nChapter: {chapter}  \n"
                return ""

            mock_read_file.side_effect = mock_read

            _ = self._call_image_search(request, payload)

            # Verify prompts were stripped before being passed to LLM
            call_args = request.state["completions_obj"].completions.call_args
            system_prompt = call_args[0][0]
            user_prompt = call_args[0][1]
            assert system_prompt == "System prompt with whitespace"
            assert user_prompt.startswith("Selected:")
            assert not user_prompt.startswith(" ")
            assert not user_prompt.endswith(" ")

    def test_image_search_validates_output_with_serializer(self):
        """Test that image_search validates the rendered output with the serializer."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render, patch("ai.views.image_search.ServerTextResponseSerializer") as mock_serializer:
            request.state["completions_obj"].completions = AsyncMock(return_value="cross resurrection")
            mock_search.return_value = ["http://example.com/img1.jpg"]
            mock_render.return_value = "<html>Response</html>"

            async def mock_read(path):
                return "Bible image search prompt"

            mock_read_file.side_effect = mock_read

            _ = self._call_image_search(request, payload)

            # Verify serializer was called with the rendered template
            mock_serializer.assert_called_once_with(response_content="<html>Response</html>")

    def _assert_500_error(self, response, message_substring):
        """Assert a 500 HTML error response containing the given message."""
        assert response.status_code == 500
        assert "text/html" in response["content-type"]
        assert message_substring.encode() in response.content

    def test_image_search_error_prompt_formatting(self):
        """Test that a failure loading/formatting prompts returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render:
            # async_read_file raises before any prompt formatting can happen
            mock_read_file.side_effect = FileNotFoundError("missing system.md")

            response = self._call_image_search(request, payload)

            self._assert_500_error(response, "Error formatting user prompt")
            # Downstream steps should never run
            mock_search.assert_not_called()
            mock_render.assert_not_called()

    def test_image_search_error_stripping_whitespace(self):
        """Test that a failure stripping prompts returns a 500 error.

        system_prompt is a non-string so .strip() raises AttributeError after the
        formatting block succeeds.
        """
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search:

            async def mock_read(path):
                if "system.md" in str(path):
                    return 123  # non-string: .strip() will raise
                elif "user.md" in str(path):
                    return "Selected: {selected_text}\nVerses: {verses_text}\nBook: {book}\nChapter: {chapter}"
                return ""

            mock_read_file.side_effect = mock_read

            response = self._call_image_search(request, payload)

            self._assert_500_error(response, "Error stripping whitespace")
            mock_search.assert_not_called()

    def test_image_search_error_generating_search_query(self):
        """Test that an LLM completions failure returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render:
            request.state["completions_obj"].completions = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

            async def mock_read(path):
                return "Bible image search prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_image_search(request, payload)

            self._assert_500_error(response, "Error generating search query")
            mock_search.assert_not_called()
            mock_render.assert_not_called()

    def test_image_search_error_searching_for_images(self):
        """Test that an image search failure returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render:
            request.state["completions_obj"].completions = AsyncMock(return_value="cross resurrection")
            mock_search.side_effect = RuntimeError("SearXNG unreachable")

            async def mock_read(path):
                return "Bible image search prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_image_search(request, payload)

            self._assert_500_error(response, "Error searching for images")
            mock_render.assert_not_called()

    def test_image_search_error_rendering_template(self):
        """Test that a template rendering failure returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render, patch("ai.views.image_search.ServerTextResponseSerializer") as mock_serializer:
            request.state["completions_obj"].completions = AsyncMock(return_value="cross resurrection")
            mock_search.return_value = ["http://example.com/img1.jpg"]
            mock_render.side_effect = RuntimeError("template missing")

            async def mock_read(path):
                return "Bible image search prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_image_search(request, payload)

            self._assert_500_error(response, "Error rendering template")
            mock_serializer.assert_not_called()

    def test_image_search_error_validating_output(self):
        """Test that a serializer validation failure returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with patch("ai.views.image_search.async_read_file") as mock_read_file, patch("ai.views.image_search.search_for_images") as mock_search, patch("ai.views.image_search.render_to_string") as mock_render, patch("ai.views.image_search.ServerTextResponseSerializer") as mock_serializer:
            request.state["completions_obj"].completions = AsyncMock(return_value="cross resurrection")
            mock_search.return_value = ["http://example.com/img1.jpg"]
            mock_render.return_value = "<html>Response</html>"
            mock_serializer.side_effect = ValueError("invalid response_content")

            async def mock_read(path):
                return "Bible image search prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_image_search(request, payload)

            self._assert_500_error(response, "Error validating output")
