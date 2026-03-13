"""Tests for the general_question API endpoint."""

import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from django.test import SimpleTestCase
from django.http import HttpRequest
from rest_framework import status

from ai.views.general_question import general_question


class TestGeneralQuestionView(SimpleTestCase):
    """Tests for the general_question API endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_path = Path("ai", "llm", "prompts", "general_question")

    def _call_general_question(self, request, payload):
        """Helper to call async general_question function."""
        return asyncio.run(general_question(request, payload))

    def test_general_question_success(self):
        """Test successful general_question endpoint with valid payload."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        # Create mock payload
        payload = MagicMock()
        payload.query = "Who is Jesus Christ?"
        payload.collection_name = "bsb"

        with patch("ai.views.general_question.async_read_file") as mock_read_file, \
             patch("ai.views.general_question.stringify_vdb_results") as mock_stringify, \
             patch("ai.views.general_question.clean_llm_output") as mock_clean, \
             patch("ai.views.general_question.render_to_string") as mock_render:

            # Mock the database and LLM calls
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(
                return_value="The Son of God!"
            )

            # Mock file reads
            async def mock_read(path):
                if "system.md" in str(path):
                    return "You are a knowledgeable Bible study assistant."
                elif "user.md" in str(path):
                    return "Question: {query}\nContext: {context}"
                return ""

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "<html>Response</html>"

            response = self._call_general_question(request, payload)

            # Verify successful response
            assert response.status_code == status.HTTP_200_OK
            assert "text/html" in response["content-type"]
            assert b"Response" in response.content

            # Verify database search was called
            request.state["milvus_db"].search.assert_called_once()
            search_call = request.state["milvus_db"].search.call_args
            assert search_call[1]["collection_name"] == "bsb"
            assert search_call[1]["query"] == "Who is Jesus Christ?"

    def test_general_question_calls_llm_completions(self):
        """Test that general_question calls the LLM completions service."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "Who is Jesus Christ?"
        payload.collection_name = "bsb"

        with patch("ai.views.general_question.async_read_file") as mock_read_file, \
             patch("ai.views.general_question.stringify_vdb_results") as mock_stringify, \
             patch("ai.views.general_question.clean_llm_output") as mock_clean, \
             patch("ai.views.general_question.render_to_string") as mock_render:

            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(
                return_value="The Son of God!"
            )

            async def mock_read(path):
                if "system.md" in str(path):
                    return "You are a knowledgeable Bible study assistant."
                elif "user.md" in str(path):
                    return "Question: {query}\nContext: {context}"
                return ""

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "Rendered template"

            _ = self._call_general_question(request, payload)

            # Verify LLM completions was called with proper prompts
            request.state["completions_obj"].completions.assert_called_once()
            call_args = request.state["completions_obj"].completions.call_args
            # First arg is system_prompt, second is user_prompt, third is query
            assert call_args[0][0] == "You are a knowledgeable Bible study assistant."  # system prompt
            assert "Who is Jesus Christ?" in call_args[0][1]  # user prompt with query
            assert call_args[0][2] == "Who is Jesus Christ?"  # query param

    def test_general_question_handles_empty_vector_results(self):
        """Test that general_question handles empty vector database results."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "Who is Jesus Christ?"
        payload.collection_name = "bsb"

        with patch("ai.views.general_question.async_read_file") as mock_read_file, \
             patch("ai.views.general_question.stringify_vdb_results") as mock_stringify, \
             patch("ai.views.general_question.clean_llm_output") as mock_clean, \
             patch("ai.views.general_question.render_to_string") as mock_render:

            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(
                return_value="The Son of God!"
            )

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = ""  # Empty vector results
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "Template"

            response = self._call_general_question(request, payload)

            assert response.status_code == status.HTTP_200_OK
            # Verify stringify was called even with empty results
            mock_stringify.assert_called_once()

    def test_general_question_loads_correct_prompt_files(self):
        """Test that general_question loads prompts from correct file paths."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "Who is Jesus Christ?"
        payload.collection_name = "bsb"

        with patch("ai.views.general_question.async_read_file") as mock_read_file, \
             patch("ai.views.general_question.stringify_vdb_results") as mock_stringify, \
             patch("ai.views.general_question.clean_llm_output") as mock_clean, \
             patch("ai.views.general_question.render_to_string") as mock_render:

            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(
                return_value="The Son of God!"
            )

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_general_question(request, payload)

            # Verify both system and user prompts were loaded
            assert mock_read_file.call_count == 2
            call_paths = [call[0][0] for call in mock_read_file.call_args_list]
            path_strings = [str(p) for p in call_paths]
            assert any("system.md" in p for p in path_strings)
            assert any("user.md" in p for p in path_strings)

    def test_general_question_renders_template(self):
        """Test that general_question renders the response template."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "Who is Jesus Christ?"
        payload.collection_name = "bsb"

        with patch("ai.views.general_question.async_read_file") as mock_read_file, \
             patch("ai.views.general_question.stringify_vdb_results") as mock_stringify, \
             patch("ai.views.general_question.clean_llm_output") as mock_clean, \
             patch("ai.views.general_question.render_to_string") as mock_render:

            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(
                return_value="The Son of God!"
            )

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "<html><body>Response</body></html>"

            _ = self._call_general_question(request, payload)

            # Verify template rendering
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == "partials/general_question.html"
            assert call_args[0][1]["response_content"] is not None

    def test_general_question_response_content_type(self):
        """Test that general_question returns HTML content type."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "Who is Jesus Christ?"
        payload.collection_name = "bsb"

        with patch("ai.views.general_question.async_read_file") as mock_read_file, \
             patch("ai.views.general_question.stringify_vdb_results") as mock_stringify, \
             patch("ai.views.general_question.clean_llm_output") as mock_clean, \
             patch("ai.views.general_question.render_to_string") as mock_render:

            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(
                return_value="The Son of God!"
            )

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "<html>Response</html>"

            response = self._call_general_question(request, payload)

            # Verify HTML content type
            assert "text/html" in response["content-type"]

    def test_general_question_uses_milvus_search_limit(self):
        """Test that general_question uses the configured MILVUS_SEARCH_LIMIT."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "Who is Jesus Christ?"
        payload.collection_name = "bsb"

        with patch("ai.views.general_question.async_read_file") as mock_read_file, \
             patch("ai.views.general_question.stringify_vdb_results") as mock_stringify, \
             patch("ai.views.general_question.clean_llm_output") as mock_clean, \
             patch("ai.views.general_question.render_to_string") as mock_render, \
             patch("ai.views.general_question.MILVUS_SEARCH_LIMIT", 5):

            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(
                return_value="The Son of God!"
            )

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_general_question(request, payload)

            # Verify MILVUS_SEARCH_LIMIT was used in search
            request.state["milvus_db"].search.assert_called_once()
            assert request.state["milvus_db"].search.call_args[1]["limit"] == 5

    def test_general_question_extracts_payload_fields(self):
        """Test that general_question correctly extracts fields from payload."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }

        payload = MagicMock()
        payload.query = "Who is Jesus Christ?"
        payload.collection_name = "bsb"

        with patch("ai.views.general_question.async_read_file") as mock_read_file, \
             patch("ai.views.general_question.stringify_vdb_results") as mock_stringify, \
             patch("ai.views.general_question.clean_llm_output") as mock_clean, \
             patch("ai.views.general_question.render_to_string") as mock_render:

            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(
                return_value="The Son of God!"
            )

            async def mock_read(path):
                return "Bible study prompt"

            mock_read_file.side_effect = mock_read
            mock_stringify.return_value = "If anyone confesses that Jesus is the Son of God, God abides in him, and he in God. (1 John 4:15)"
            mock_clean.return_value = "<p>The Son of God!</p>"
            mock_render.return_value = "<html>Response</html>"

            _ = self._call_general_question(request, payload)

            # Verify correct fields were extracted and used
            assert request.state["milvus_db"].search.call_args[1]["query"] == "Who is Jesus Christ?"
            assert request.state["milvus_db"].search.call_args[1]["collection_name"] == "bsb"
