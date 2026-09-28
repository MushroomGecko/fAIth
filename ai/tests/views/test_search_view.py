"""Tests for the search API endpoint."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.http import HttpRequest
from django.test import SimpleTestCase
from ninja.testing import TestAsyncClient

from ai.views.search import router, search


class TestSearchView(SimpleTestCase):
    """Tests for the search API endpoint."""

    def _call_search(self, request, payload):
        """Call the async search function from a synchronous test."""
        return asyncio.run(search(request, payload))

    def _build_request(self):
        request = HttpRequest()
        request.method = "POST"
        request.state = {"milvus_db": MagicMock()}
        request.state["milvus_db"].search = AsyncMock()
        return request

    def _build_payload(self, query="love", collection_name="bsb"):
        payload = MagicMock()
        payload.query = query
        payload.collection_name = collection_name
        return payload

    def _patch_dependencies(self, vector_results=None, direct_results=None):
        """Return patches and configure the external search dependencies."""
        patches = (
            patch("ai.views.search.ripgrep_bible", new_callable=AsyncMock),
            patch("ai.views.search.clean_llm_output", new_callable=AsyncMock),
            patch("ai.views.search.render_to_string"),
        )
        mock_ripgrep, mock_clean, mock_render = (item.start() for item in patches)
        mock_ripgrep.return_value = direct_results or []
        mock_clean.return_value = "<p>cleaned results</p>"
        mock_render.return_value = "<html>results</html>"
        self.addCleanup(patches[0].stop)
        self.addCleanup(patches[1].stop)
        self.addCleanup(patches[2].stop)
        return mock_ripgrep, mock_clean, mock_render

    def test_search_success(self):
        """A successful search returns the rendered HTML response."""
        request = self._build_request()
        payload = self._build_payload()
        request.state["milvus_db"].search.return_value = [
            {"book": "John", "chapter": 3, "verse": 16, "text": "God so loved"},
        ]
        mock_ripgrep, mock_clean, mock_render = self._patch_dependencies(
            direct_results=[
                {"book": "Romans", "chapter": 5, "verse": 8, "text": "God demonstrates love"},
            ]
        )

        response = self._call_search(request, payload)

        assert response.status_code == 200
        assert response["content-type"].startswith("text/html")
        assert response.content == b"<html>results</html>"
        mock_ripgrep.assert_awaited_once_with("love", "bsb")
        mock_clean.assert_awaited_once()
        mock_render.assert_called_once_with(
            "partials/server_response_partial.html",
            {"response_content": mock_clean.return_value},
        )

    def test_search_uses_configured_milvus_limit(self):
        """The configured result limit is passed to the vector database."""
        request = self._build_request()
        payload = self._build_payload()
        request.state["milvus_db"].search.return_value = []
        self._patch_dependencies()

        with patch("ai.views.search.MILVUS_SEARCH_LIMIT", 7):
            self._call_search(request, payload)

        request.state["milvus_db"].search.assert_awaited_once_with(collection_name="bsb", query="love", limit=7)

    def test_search_sorts_and_formats_both_result_sets(self):
        """Results are ordered by canonical book order, chapter, and verse."""
        request = self._build_request()
        payload = self._build_payload(query="faith")
        request.state["milvus_db"].search.return_value = [
            {"book": "Romans", "chapter": 5, "verse": 8, "text": "vector Romans"},
            {"book": "Genesis", "chapter": 2, "verse": 1, "text": "vector Genesis 2"},
            {"book": "Genesis", "chapter": 1, "verse": 2, "text": "vector Genesis 1:2"},
            {"book": "Genesis", "chapter": 1, "verse": 1, "text": "vector Genesis 1:1"},
        ]
        _, mock_clean, _ = self._patch_dependencies(
            direct_results=[
                {"book": "John", "chapter": 3, "verse": 16, "text": "direct John"},
                {"book": "Exodus", "chapter": 2, "verse": 1, "text": "direct Exodus 2"},
                {"book": "Exodus", "chapter": 1, "verse": 2, "text": "direct Exodus 1:2"},
                {"book": "Exodus", "chapter": 1, "verse": 1, "text": "direct Exodus 1:1"},
            ]
        )

        self._call_search(request, payload)

        final_response = mock_clean.call_args.args[0]
        assert "##Search results for 'faith'" in final_response
        vector_order = [
            final_response.index("vector Genesis 1:1"),
            final_response.index("vector Genesis 1:2"),
            final_response.index("vector Genesis 2"),
            final_response.index("vector Romans"),
        ]
        direct_order = [
            final_response.index("direct Exodus 1:1"),
            final_response.index("direct Exodus 1:2"),
            final_response.index("direct Exodus 2"),
            final_response.index("direct John"),
        ]
        assert vector_order == sorted(vector_order)
        assert direct_order == sorted(direct_order)
        assert "(Genesis 1:1)" in final_response
        assert "(Exodus 1:1)" in final_response

    def test_search_handles_empty_results(self):
        """Empty vector and direct searches still produce a successful response."""
        request = self._build_request()
        payload = self._build_payload()
        request.state["milvus_db"].search.return_value = []
        mock_ripgrep, _, mock_render = self._patch_dependencies()

        response = self._call_search(request, payload)

        assert response.status_code == 200
        mock_ripgrep.assert_awaited_once()
        mock_render.assert_called_once()

    def _assert_500_error(self, response, message):
        assert response.status_code == 500
        assert response["content-type"].startswith("text/html")
        assert message.encode() in response.content

    def test_search_error_searching_vector_database(self):
        request = self._build_request()
        request.state["milvus_db"].search.side_effect = RuntimeError("Milvus unavailable")
        mock_ripgrep, _, mock_render = self._patch_dependencies()

        response = self._call_search(request, self._build_payload())

        self._assert_500_error(response, "Error searching vector database")
        mock_ripgrep.assert_not_awaited()
        mock_render.assert_not_called()

    def test_search_error_sorting_vector_results(self):
        request = self._build_request()
        request.state["milvus_db"].search.return_value = [{"book": "John"}]
        mock_ripgrep, _, mock_render = self._patch_dependencies()

        response = self._call_search(request, self._build_payload())

        self._assert_500_error(response, "Error sorting vector results")
        mock_ripgrep.assert_not_awaited()
        mock_render.assert_not_called()

    def test_search_error_searching_bible(self):
        request = self._build_request()
        request.state["milvus_db"].search.return_value = []
        mock_ripgrep, _, mock_render = self._patch_dependencies()
        mock_ripgrep.side_effect = RuntimeError("Bible unavailable")

        response = self._call_search(request, self._build_payload())

        self._assert_500_error(response, "Error searching Bible")
        mock_render.assert_not_called()

    def test_search_error_cleaning_output(self):
        request = self._build_request()
        request.state["milvus_db"].search.return_value = []
        _, mock_clean, mock_render = self._patch_dependencies()
        mock_clean.side_effect = RuntimeError("cleaner unavailable")

        response = self._call_search(request, self._build_payload())

        self._assert_500_error(response, "Error cleaning LLM output")
        mock_render.assert_not_called()

    def test_search_error_rendering_template(self):
        request = self._build_request()
        request.state["milvus_db"].search.return_value = []
        _, _, mock_render = self._patch_dependencies()
        mock_render.side_effect = RuntimeError("template unavailable")

        response = self._call_search(request, self._build_payload())

        self._assert_500_error(response, "Error rendering template")

    def test_search_error_validating_output(self):
        request = self._build_request()
        request.state["milvus_db"].search.return_value = []
        self._patch_dependencies()
        with patch("ai.views.search.ServerTextResponseSerializer", side_effect=ValueError("invalid")):
            response = self._call_search(request, self._build_payload())

        self._assert_500_error(response, "Error validating output")

    @pytest.mark.asyncio
    async def test_search_rejects_invalid_payload_with_422(self):
        """Ninja rejects an empty query before entering the view."""
        client = TestAsyncClient(router)

        response = await client.post(
            "/search",
            data={"collection_name": "bsb", "query": ""},
        )

        assert response.status_code == 422
