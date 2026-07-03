"""Tests for the ask_selected API endpoint."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from django.http import HttpRequest
from django.test import SimpleTestCase

from ai.views.ask_selected import ask_selected


class TestAskSelectedView(SimpleTestCase):
    """Tests for the ask_selected API endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_path = Path("ai", "llm", "prompts", "ask_selected")

    def _call_ask_selected(self, request, payload):
        """Helper to call async ask_selected function."""
        return asyncio.run(ask_selected(request, payload))

    def test_ask_selected_success(self):
        """Test successful ask_selected endpoint with valid payload."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        # Create mock payload
        payload = MagicMock()
        payload.query = "What does this mean?"
        payload.selected_text = "For God so loved the world"
        payload.collection_name = "bsb"

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
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "What does this mean?"
        payload.selected_text = "For God so loved the world"
        payload.collection_name = "bsb"

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
                    return "Selected text: {selected_text}\nQuestion: {query}\nContext: {context}"
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
            assert call_args[0][2] == "What does this mean?"  # query param

    def test_ask_selected_handles_empty_vector_results(self):
        """Test that ask_selected handles empty vector database results."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "What does this mean?"
        payload.selected_text = "For God so loved the world"
        payload.collection_name = "bsb"

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
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "What does this mean?"
        payload.selected_text = "For God so loved the world"
        payload.collection_name = "bsb"

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
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "What does this mean?"
        payload.selected_text = "For God so loved the world"
        payload.collection_name = "bsb"

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
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "What does this mean?"
        payload.selected_text = "For God so loved the world"
        payload.collection_name = "bsb"

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
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "What does this mean?"
        payload.selected_text = "For God so loved the world"
        payload.collection_name = "bsb"

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
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "What does this mean?"
        payload.selected_text = "For God so loved the world"
        payload.collection_name = "bsb"

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
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "What does this mean?"
        payload.selected_text = "For God so loved the world"
        payload.collection_name = "bsb"

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
