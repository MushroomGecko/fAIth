"""Tests for the definition_search API endpoint."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.http import HttpRequest
from django.test import SimpleTestCase
from ninja.testing import TestAsyncClient

from ai.views.definition_search import definition_search, router


class TestDefinitionSearchView(SimpleTestCase):
    """Tests for the definition_search API endpoint."""

    def _call_definition_search(self, request, payload):
        """Call the async definition_search function from a synchronous test."""
        return asyncio.run(definition_search(request, payload))

    def _build_request(self):
        """Build a request with the state required by the endpoint."""
        request = HttpRequest()
        request.method = "POST"
        request.state = {
            "milvus_db": AsyncMock(),
            "completions_obj": AsyncMock(),
        }
        return request

    def _build_payload(self):
        """Build a mock payload matching DefinitionSearchInputSerializer fields."""
        payload = MagicMock()
        payload.selected_text = "love"
        payload.verses_text = "For God so loved the world, that He gave His one and only Son."
        payload.book = "John"
        payload.chapter = "3"
        payload.collection_name = "bsb"
        return payload

    def _configure_success(self, request, mock_read_file, mock_unify, mock_stringify):
        """Configure common downstream mocks for a successful request."""
        request.state["milvus_db"].search = AsyncMock(return_value=[])
        request.state["completions_obj"].completions = AsyncMock(return_value="A definition.")
        mock_unify.return_value = ["unified result"]
        mock_stringify.return_value = "Biblical context"

        async def mock_read(path):
            if "system.md" in str(path):
                return "Definition assistant"
            return (
                "Selected: {selected_text}\nVerses: {verses_text}\n"
                "Reference: {book} {chapter} ({collection_name})\n"
                "Vector: {vector_context}\nLexical: {definition_context}"
            )

        mock_read_file.side_effect = mock_read

    def _assert_500_error(self, response, message):
        """Assert that the endpoint returned an HTML 500 response."""
        assert response.status_code == 500
        assert "text/html" in response["content-type"]
        assert message.encode() in response.content

    def test_definition_search_success(self):
        """A valid request returns the rendered definition."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.definition_search.async_read_file") as mock_read_file,
            patch("ai.views.definition_search.unify_vdb_results") as mock_unify,
            patch("ai.views.definition_search.stringify_vdb_results") as mock_stringify,
            patch("ai.views.definition_search.definition_query", new_callable=AsyncMock) as mock_definition,
            patch("ai.views.definition_search.clean_llm_output", new_callable=AsyncMock) as mock_clean,
            patch("ai.views.definition_search.render_to_string") as mock_render,
        ):
            self._configure_success(request, mock_read_file, mock_unify, mock_stringify)
            mock_definition.return_value = "  lexical definition  "
            mock_clean.return_value = "<p>A definition.</p>"
            mock_render.return_value = "<html>Definition</html>"

            response = self._call_definition_search(request, payload)

            assert response.status_code == 200
            assert response.content == b"<html>Definition</html>"
            assert "text/html" in response["content-type"]
            mock_definition.assert_awaited_once_with("love", request)

    def test_definition_search_searches_verses_and_selection(self):
        """The vector database is searched with both contextual queries."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.definition_search.async_read_file") as mock_read_file,
            patch("ai.views.definition_search.unify_vdb_results") as mock_unify,
            patch("ai.views.definition_search.stringify_vdb_results") as mock_stringify,
            patch("ai.views.definition_search.definition_query", new_callable=AsyncMock) as mock_definition,
            patch("ai.views.definition_search.clean_llm_output", new_callable=AsyncMock) as mock_clean,
            patch("ai.views.definition_search.render_to_string") as mock_render,
            patch("ai.views.definition_search.MILVUS_SEARCH_LIMIT", 10),
        ):
            self._configure_success(request, mock_read_file, mock_unify, mock_stringify)
            mock_definition.return_value = "definition"
            mock_clean.return_value = "<p>Definition</p>"
            mock_render.return_value = "Rendered"

            self._call_definition_search(request, payload)

            calls = request.state["milvus_db"].search.call_args_list
            assert len(calls) == 2
            assert calls[0].kwargs == {"collection_name": "bsb", "query": payload.verses_text, "limit": 5}
            assert calls[1].kwargs == {"collection_name": "bsb", "query": "love", "limit": 5}
            mock_unify.assert_awaited_once_with([])

    def test_definition_search_passes_all_context_to_llm(self):
        """The LLM receives formatted biblical, lexical, and payload context."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.definition_search.async_read_file") as mock_read_file,
            patch("ai.views.definition_search.unify_vdb_results") as mock_unify,
            patch("ai.views.definition_search.stringify_vdb_results") as mock_stringify,
            patch("ai.views.definition_search.definition_query", new_callable=AsyncMock) as mock_definition,
            patch("ai.views.definition_search.clean_llm_output", new_callable=AsyncMock) as mock_clean,
            patch("ai.views.definition_search.render_to_string") as mock_render,
        ):
            self._configure_success(request, mock_read_file, mock_unify, mock_stringify)
            mock_definition.return_value = "lexical definition"
            mock_clean.return_value = "<p>Definition</p>"
            mock_render.return_value = "Rendered"

            self._call_definition_search(request, payload)

            system_prompt, user_prompt = request.state["completions_obj"].completions.call_args.args
            assert system_prompt == "Definition assistant"
            for value in ("love", payload.verses_text, "John", "3", "bsb", "Biblical context", "lexical definition"):
                assert value in user_prompt
            mock_read_file.assert_awaited()
            assert {str(call.args[0]).split("/")[-1] for call in mock_read_file.call_args_list} == {
                "system.md",
                "user.md",
            }

    def test_definition_search_strips_definition_result_and_prompts(self):
        """Whitespace is removed before lexical output and prompts are used."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.definition_search.async_read_file") as mock_read_file,
            patch("ai.views.definition_search.unify_vdb_results") as mock_unify,
            patch("ai.views.definition_search.stringify_vdb_results") as mock_stringify,
            patch("ai.views.definition_search.definition_query", new_callable=AsyncMock) as mock_definition,
            patch("ai.views.definition_search.clean_llm_output", new_callable=AsyncMock) as mock_clean,
            patch("ai.views.definition_search.render_to_string") as mock_render,
        ):
            self._configure_success(request, mock_read_file, mock_unify, mock_stringify)
            mock_definition.return_value = "  lexical definition  "
            mock_clean.return_value = "<p>Definition</p>"
            mock_render.return_value = "Rendered"

            self._call_definition_search(request, payload)

            system_prompt, user_prompt = request.state["completions_obj"].completions.call_args.args
            assert system_prompt == "Definition assistant"
            assert user_prompt.startswith("Selected:")
            assert not user_prompt.endswith(" ")

    def test_definition_search_renders_and_validates_output(self):
        """The cleaned result is marked safe, rendered, and validated."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.definition_search.async_read_file") as mock_read_file,
            patch("ai.views.definition_search.unify_vdb_results") as mock_unify,
            patch("ai.views.definition_search.stringify_vdb_results") as mock_stringify,
            patch("ai.views.definition_search.definition_query", new_callable=AsyncMock) as mock_definition,
            patch("ai.views.definition_search.clean_llm_output", new_callable=AsyncMock) as mock_clean,
            patch("ai.views.definition_search.render_to_string") as mock_render,
            patch("ai.views.definition_search.mark_safe") as mock_safe,
            patch("ai.views.definition_search.ServerTextResponseSerializer") as mock_serializer,
        ):
            self._configure_success(request, mock_read_file, mock_unify, mock_stringify)
            mock_definition.return_value = "definition"
            mock_clean.return_value = "<p>Definition</p>"
            mock_safe.return_value = "safe definition"
            mock_render.return_value = "<html>Response</html>"

            self._call_definition_search(request, payload)

            mock_safe.assert_called_once_with("<p>Definition</p>")
            mock_render.assert_called_once_with(
                "partials/server_response_partial.html", {"response_content": "safe definition"}
            )
            mock_serializer.assert_called_once_with(response_content="<html>Response</html>")

    def test_definition_search_error_searching_vector_database(self):
        """A vector search failure returns a 500 response."""
        request = self._build_request()
        payload = self._build_payload()
        request.state["milvus_db"].search = AsyncMock(side_effect=RuntimeError("Milvus unavailable"))

        with patch("ai.views.definition_search.render_to_string") as mock_render:
            response = self._call_definition_search(request, payload)

        self._assert_500_error(response, "Error searching vector database")
        mock_render.assert_not_called()

    def test_definition_search_error_unifying_results(self):
        """A vector result unification failure returns a 500 response."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.definition_search.unify_vdb_results", new_callable=AsyncMock) as mock_unify,
            patch("ai.views.definition_search.definition_query", new_callable=AsyncMock) as mock_definition,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            mock_unify.side_effect = RuntimeError("unification failed")

            response = self._call_definition_search(request, payload)

        self._assert_500_error(response, "Error unifying vector database results")
        mock_definition.assert_not_awaited()

    def test_definition_search_error_searching_wordnet(self):
        """A lexical lookup failure returns a 500 response."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.definition_search.unify_vdb_results", new_callable=AsyncMock) as mock_unify,
            patch("ai.views.definition_search.stringify_vdb_results", new_callable=AsyncMock) as mock_stringify,
            patch("ai.views.definition_search.definition_query", new_callable=AsyncMock) as mock_definition,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            mock_unify.return_value = []
            mock_stringify.return_value = ""
            mock_definition.side_effect = RuntimeError("WordNet unavailable")

            response = self._call_definition_search(request, payload)

        self._assert_500_error(response, "Error searching WordNet")

    def test_definition_search_error_formatting_prompt(self):
        """A prompt-loading or formatting failure returns a 500 response."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.definition_search.async_read_file", new_callable=AsyncMock) as mock_read_file,
            patch("ai.views.definition_search.unify_vdb_results", new_callable=AsyncMock) as mock_unify,
            patch("ai.views.definition_search.stringify_vdb_results", new_callable=AsyncMock) as mock_stringify,
            patch("ai.views.definition_search.definition_query", new_callable=AsyncMock) as mock_definition,
            patch("ai.views.definition_search.render_to_string") as mock_render,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            mock_unify.return_value = []
            mock_stringify.return_value = ""
            mock_definition.return_value = "definition"
            mock_read_file.side_effect = FileNotFoundError("missing prompt")

            response = self._call_definition_search(request, payload)

        self._assert_500_error(response, "Error formatting user prompt")
        mock_render.assert_not_called()

    def test_definition_search_error_stripping_prompt(self):
        """A non-string prompt causes the dedicated stripping error response."""
        request = self._build_request()
        payload = self._build_payload()

        with (
            patch("ai.views.definition_search.async_read_file", new_callable=AsyncMock) as mock_read_file,
            patch("ai.views.definition_search.unify_vdb_results", new_callable=AsyncMock) as mock_unify,
            patch("ai.views.definition_search.stringify_vdb_results", new_callable=AsyncMock) as mock_stringify,
            patch("ai.views.definition_search.definition_query", new_callable=AsyncMock) as mock_definition,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            mock_unify.return_value = []
            mock_stringify.return_value = ""
            mock_definition.return_value = "definition"

            async def mock_read(path):
                return 123 if "system.md" in str(path) else "Selected: {selected_text}"

            mock_read_file.side_effect = mock_read
            response = self._call_definition_search(request, payload)

        self._assert_500_error(response, "Error stripping whitespace")

    def _run_late_stage_error_test(self, stage, expected_message):
        """Run a common setup for failures after prompt preparation."""
        request = self._build_request()
        payload = self._build_payload()
        patches = {
            "llm": ("ai.views.definition_search.clean_llm_output", RuntimeError("LLM failed")),
            "clean": ("ai.views.definition_search.clean_llm_output", RuntimeError("clean failed")),
            "render": ("ai.views.definition_search.render_to_string", RuntimeError("render failed")),
            "serializer": (
                "ai.views.definition_search.ServerTextResponseSerializer",
                ValueError("invalid output"),
            ),
        }

        with (
            patch("ai.views.definition_search.async_read_file", new_callable=AsyncMock) as mock_read_file,
            patch("ai.views.definition_search.unify_vdb_results", new_callable=AsyncMock) as mock_unify,
            patch("ai.views.definition_search.stringify_vdb_results", new_callable=AsyncMock) as mock_stringify,
            patch("ai.views.definition_search.definition_query", new_callable=AsyncMock) as mock_definition,
            patch("ai.views.definition_search.clean_llm_output", new_callable=AsyncMock) as mock_clean,
            patch("ai.views.definition_search.render_to_string") as mock_render,
            patch("ai.views.definition_search.ServerTextResponseSerializer") as mock_serializer,
        ):
            request.state["milvus_db"].search = AsyncMock(return_value=[])
            request.state["completions_obj"].completions = AsyncMock(return_value="raw")
            mock_read_file.return_value = "Prompt"
            mock_unify.return_value = []
            mock_stringify.return_value = "context"
            mock_definition.return_value = "definition"
            mock_clean.return_value = "<p>clean</p>"
            mock_render.return_value = "Rendered"

            if stage == "llm":
                request.state["completions_obj"].completions.side_effect = patches[stage][1]
            elif stage == "clean":
                mock_clean.side_effect = patches[stage][1]
            elif stage == "render":
                mock_render.side_effect = patches[stage][1]
            else:
                mock_serializer.side_effect = patches[stage][1]

            response = self._call_definition_search(request, payload)

        self._assert_500_error(response, expected_message)

    def test_definition_search_error_generating_llm_response(self):
        """An LLM failure returns a 500 response."""
        self._run_late_stage_error_test("llm", "Error generating LLM response")

    def test_definition_search_error_cleaning_output(self):
        """A response-cleaning failure returns a 500 response."""
        self._run_late_stage_error_test("clean", "Error cleaning LLM output")

    def test_definition_search_error_rendering_template(self):
        """A template-rendering failure returns a 500 response."""
        self._run_late_stage_error_test("render", "Error rendering template")

    def test_definition_search_error_validating_output(self):
        """An output serializer failure returns a 500 response."""
        self._run_late_stage_error_test("serializer", "Error validating output")

    @pytest.mark.asyncio
    async def test_definition_search_rejects_invalid_payload_with_422(self):
        """An empty selected_text is rejected before the view body runs."""
        client = TestAsyncClient(router)
        response = await client.post(
            "/definition_search",
            data={
                "selected_text": "",
                "verses_text": "For God so loved the world.",
                "book": "John",
                "chapter": "3",
                "collection_name": "bsb",
            },
        )

        assert response.status_code == 422
