"""Tests for the ask_selected API endpoint."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.http import HttpRequest
from django.test import SimpleTestCase
from ninja.testing import TestAsyncClient

from ai.views.ask_selected import ask_selected, router


class TestAskSelectedView(SimpleTestCase):
    """Tests for the ask_selected API endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_path = Path("ai", "llm", "prompts", "ask_selected")

    def _call_ask_selected(self, request, payload):
        """Helper to call async ask_selected function."""
        return asyncio.run(ask_selected(request, payload))

    def _build_request(self):
        """Build a request with the required state."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }
        return request

    def _build_payload(self):
        """Build a mock payload matching AskSelectedInputSerializer fields."""
        payload = MagicMock()
        payload.query = "What does this mean?"
        payload.selected_text = "For God so loved the world"
        payload.verses_text = "16) For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life."
        payload.book = "John"
        payload.chapter = "3"
        payload.collection_name = "bsb"
        return payload

    def test_ask_selected_success(self):
        """Test successful ask_selected endpoint with valid payload."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.stringify_vdb_results") as mock_stringify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            # Mock the database and LLM calls
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(return_value="The Son of God!")

            # Mock file reads
            async def mock_read(path):
                if "system.md" in str(path):
                    return "You are a knowledgeable Bible study assistant."
                elif "user.md" in str(path):
                    return "Selected text: {selected_text}\nQuestion: {query}\nContext: {context}"
                return ""

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = (
                "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            )
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "<html>Response</html>"

            response = self._call_ask_selected(request, payload)

            # Verify successful response
            assert response.status_code == 200
            assert "text/html" in response["content-type"]
            assert b"Response" in response.content

            # Verify database search was called twice (once for query, once for selected_text)
            assert request.state["milvus_db"].search.call_count == 2
            search_calls = request.state["milvus_db"].search.call_args_list
            # Both calls should have same collection_name
            assert search_calls[0][1]["collection_name"] == "bsb"
            assert search_calls[1][1]["collection_name"] == "bsb"
            # Verify queries
            assert search_calls[0][1]["query"] == "What does this mean?"
            assert search_calls[1][1]["query"] == "For God so loved the world"

    def test_ask_selected_calls_llm_completions(self):
        """Test that ask_selected calls the LLM completions service."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.stringify_vdb_results") as mock_stringify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(return_value="The Son of God!")

            async def mock_read(path):
                if "system.md" in str(path):
                    return "You are a knowledgeable Bible study assistant."
                elif "user.md" in str(path):
                    return (
                        "Selected text: {selected_text}\nQuestion: {query}\nContext: {context}\n"
                        "Verses: {verses_text}\nBook: {book}\nChapter: {chapter}\nVersion: {collection_name}"
                    )
                return ""

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = (
                "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            )
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "Rendered template"

            _ = self._call_ask_selected(request, payload)

            # Verify LLM completions was called with proper prompts
            request.state["completions_obj"].completions.assert_called_once()
            call_args = request.state["completions_obj"].completions.call_args
            # First arg is system_prompt, second is user_prompt, third is query
            assert call_args[0][0] == "You are a knowledgeable Bible study assistant."  # system prompt
            assert "For God so loved the world" in call_args[0][1]  # user prompt with selected_text
            assert "What does this mean?" in call_args[0][1]  # user prompt with query
            # All payload fields should be interpolated into the user prompt
            assert "16) For God so loved the world" in call_args[0][1]  # verses_text
            assert "John" in call_args[0][1]  # book
            assert "3" in call_args[0][1]  # chapter
            assert "bsb" in call_args[0][1]  # collection_name
            assert call_args[0][2] == "What does this mean?"  # query param

    def test_ask_selected_handles_empty_vector_results(self):
        """Test that ask_selected handles empty vector database results."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.unify_vdb_results") as mock_unify,
            patch("ai.views.ask_selected.stringify_vdb_results") as mock_stringify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(return_value="The Son of God!")

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read
            mock_unify.return_value = []  # Empty after unification
            mock_stringify.return_value = ""  # Empty vector results
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "Template"

            response = self._call_ask_selected(request, payload)

            assert response.status_code == 200
            # Verify stringify was called once on unified results (not twice)
            assert mock_stringify.call_count == 1

    def test_ask_selected_loads_correct_prompt_files(self):
        """Test that ask_selected loads prompts from correct file paths."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.stringify_vdb_results") as mock_stringify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(return_value="The Son of God!")

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = (
                "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            )
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_ask_selected(request, payload)

            # Verify both system and user prompts were loaded
            assert mock_read_file.call_count == 2
            call_paths = [call[0][0] for call in mock_read_file.call_args_list]
            path_strings = [str(p) for p in call_paths]
            assert any("system.md" in p for p in path_strings)
            assert any("user.md" in p for p in path_strings)

    def test_ask_selected_renders_template(self):
        """Test that ask_selected renders the response template."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.stringify_vdb_results") as mock_stringify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(return_value="The Son of God!")

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = (
                "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            )
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "<html><body>Response</body></html>"

            _ = self._call_ask_selected(request, payload)

            # Verify template rendering
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == "partials/text.html"
            assert call_args[0][1]["response_content"] is not None

    def test_ask_selected_response_content_type(self):
        """Test that ask_selected returns HTML content type."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.stringify_vdb_results") as mock_stringify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(return_value="The Son of God!")

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = (
                "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            )
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "<html>Response</html>"

            response = self._call_ask_selected(request, payload)

            # Verify HTML content type
            assert "text/html" in response["content-type"]

    def test_ask_selected_uses_milvus_search_limit(self):
        """Test that ask_selected uses the configured MILVUS_SEARCH_LIMIT."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.stringify_vdb_results") as mock_stringify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
            patch("ai.views.ask_selected.MILVUS_SEARCH_LIMIT", 10),
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(return_value="The Son of God!")

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = (
                "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            )
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_ask_selected(request, payload)

            # Verify MILVUS_SEARCH_LIMIT was used in searches (half limit for each search)
            assert request.state["milvus_db"].search.call_count == 2
            search_calls = request.state["milvus_db"].search.call_args_list
            # Each search should use half the limit (10 / 2 = 5)
            assert search_calls[0][1]["limit"] == 5
            assert search_calls[1][1]["limit"] == 5

    def test_ask_selected_extracts_payload_fields(self):
        """Test that ask_selected correctly extracts fields from payload."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.stringify_vdb_results") as mock_stringify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(return_value="The Son of God!")

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = (
                "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            )
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_ask_selected(request, payload)

            # Verify correct fields were extracted and used
            search_calls = request.state["milvus_db"].search.call_args_list
            # Both searches use same collection
            assert search_calls[0][1]["collection_name"] == "bsb"
            assert search_calls[1][1]["collection_name"] == "bsb"
            # Query is used for first search, selected_text for second
            assert search_calls[0][1]["query"] == "What does this mean?"
            assert search_calls[1][1]["query"] == "For God so loved the world"

    def test_ask_selected_combines_vector_results(self):
        """Test that ask_selected combines results from both searches."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.unify_vdb_results") as mock_unify,
            patch("ai.views.ask_selected.stringify_vdb_results") as mock_stringify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(return_value="The Son of God!")

            async def mock_read(path):
                if "system.md" in str(path):
                    return "You are a knowledgeable Bible study assistant."
                elif "user.md" in str(path):
                    return "Selected text: {selected_text}\nQuestion: {query}\nContext: {context}"
                return ""

            mock_read_file.side_effect = mock_read
            # Unified results stringified into combined context
            mock_unify.return_value = []
            mock_stringify.return_value = "Combined results from both searches"
            mock_clean.return_value = "<p>Combined response</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_ask_selected(request, payload)

            # Verify LLM was called with combined context
            call_args = request.state["completions_obj"].completions.call_args
            user_prompt = call_args[0][1]
            # The combined context should be in the prompt
            assert "Combined results from both searches" in user_prompt

    def _assert_500_error(self, response, message_substring):
        """Assert a 500 HTML error response containing the given message."""
        assert response.status_code == 500
        assert "text/html" in response["content-type"]
        assert message_substring.encode() in response.content

    def test_ask_selected_error_searching_vector_database(self):
        """Test that a vector database search failure returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.unify_vdb_results") as mock_unify,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(side_effect=RuntimeError("Milvus unreachable"))

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_ask_selected(request, payload)

            self._assert_500_error(response, "Error searching vector database")
            mock_unify.assert_not_called()
            mock_render.assert_not_called()

    def test_ask_selected_error_unifying_vector_database_results(self):
        """Test that a failure unifying/stringifying VDB results returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.unify_vdb_results") as mock_unify,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            mock_unify.side_effect = RuntimeError("unify failed")

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_ask_selected(request, payload)

            self._assert_500_error(response, "Error unifying vector database results")
            mock_render.assert_not_called()

    def test_ask_selected_error_formatting_user_prompt(self):
        """Test that a failure loading/formatting prompts returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.unify_vdb_results") as mock_unify,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            mock_unify.return_value = []
            # async_read_file raises before any prompt formatting can happen
            mock_read_file.side_effect = FileNotFoundError("missing system.md")

            response = self._call_ask_selected(request, payload)

            self._assert_500_error(response, "Error formatting user prompt")
            mock_render.assert_not_called()

    def test_ask_selected_error_stripping_whitespace(self):
        """Test that a failure stripping prompts returns a 500 error.

        system_prompt is a non-string so .strip() raises AttributeError after the
        formatting block succeeds.
        """
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.unify_vdb_results") as mock_unify,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            mock_unify.return_value = []

            async def mock_read(path):
                if "system.md" in str(path):
                    return 123  # non-string: .strip() will raise
                elif "user.md" in str(path):
                    return "Selected text: {selected_text}\nQuestion: {query}\nContext: {context}"
                return ""

            mock_read_file.side_effect = mock_read

            response = self._call_ask_selected(request, payload)

            self._assert_500_error(response, "Error stripping whitespace")
            mock_render.assert_not_called()

    def test_ask_selected_error_generating_llm_response(self):
        """Test that an LLM completions failure returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.unify_vdb_results") as mock_unify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            mock_unify.return_value = []
            request.state["completions_obj"].completions = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_ask_selected(request, payload)

            self._assert_500_error(response, "Error generating LLM response")
            mock_clean.assert_not_called()
            mock_render.assert_not_called()

    def test_ask_selected_error_cleaning_llm_output(self):
        """Test that a failure cleaning LLM output returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.unify_vdb_results") as mock_unify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            mock_unify.return_value = []
            request.state["completions_obj"].completions = AsyncMock(return_value="raw markdown")
            mock_clean.side_effect = RuntimeError("cleaner failed")

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_ask_selected(request, payload)

            self._assert_500_error(response, "Error cleaning LLM output")
            mock_render.assert_not_called()

    def test_ask_selected_error_rendering_template(self):
        """Test that a template rendering failure returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.unify_vdb_results") as mock_unify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
            patch("ai.views.ask_selected.ServerTextResponseSerializer") as mock_serializer,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            mock_unify.return_value = []
            request.state["completions_obj"].completions = AsyncMock(return_value="raw markdown")
            mock_clean.return_value = "<p>Response</p>"
            mock_render.side_effect = RuntimeError("template missing")

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_ask_selected(request, payload)

            self._assert_500_error(response, "Error rendering template")
            mock_serializer.assert_not_called()

    def test_ask_selected_error_validating_output(self):
        """Test that a serializer validation failure returns a 500 error."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.ask_selected.async_read_file") as mock_read_file,
            patch("ai.views.ask_selected.unify_vdb_results") as mock_unify,
            patch("ai.views.ask_selected.clean_llm_output") as mock_clean,
            patch("ai.views.ask_selected.render_to_string") as mock_render,
            patch("ai.views.ask_selected.ServerTextResponseSerializer") as mock_serializer,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            mock_unify.return_value = []
            request.state["completions_obj"].completions = AsyncMock(return_value="raw markdown")
            mock_clean.return_value = "<p>Response</p>"
            mock_render.return_value = "<html>Response</html>"
            mock_serializer.side_effect = ValueError("invalid response_content")

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read

            response = self._call_ask_selected(request, payload)

            self._assert_500_error(response, "Error validating output")

    @pytest.mark.asyncio
    async def test_ask_selected_rejects_invalid_payload_with_422(self):
        """A request failing input serializer validation is rejected by ninja with 422.

        This exercises the full Form(...) binding pipeline through the router, proving
        that an invalid payload never reaches the view body (so request.state is never
        accessed and no downstream mocks are required).
        """
        client = TestAsyncClient(router)
        response = await client.post(
            "/ask_selected",
            data={
                "selected_text": "For God so loved the world",
                "verses_text": "16) For God so loved the world, that he gave his only begotten Son.",
                "book": "John",
                "chapter": "3",
                "collection_name": "bsb",
                "query": "",  # empty -> fails validate_query
            },
        )

        assert response.status_code == 422
