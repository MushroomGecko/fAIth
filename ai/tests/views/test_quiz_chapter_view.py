"""Tests for the quiz_chapter API endpoint."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.http import HttpRequest
from django.test import SimpleTestCase
from ninja.testing import TestAsyncClient

from ai.views.quiz_chapter import quiz_chapter, router

ALL_VERSES = {"bsb": {"Genesis": {1: {"1": "In the beginning God created the heavens and the earth."}}}}


def _quiz_response():
    return {
        "quiz": [
            {
                "question": f"Question {index}",
                "explanation": f"Explanation {index}",
                "book": "Genesis",
                "chapter": "1",
                "verse_number": 1,
                "verse_text": "In the beginning God created the heavens and the earth.",
                "options": {"a": "One", "b": "Two", "c": "Three", "d": "Four"},
                "answer": "a",
            }
            for index in range(10)
        ]
    }


class TestQuizChapterView(SimpleTestCase):
    def _call_view(self, request, payload):
        return asyncio.run(quiz_chapter(request, payload))

    def _build_request(self, completions=None):
        request = HttpRequest()
        request.method = "POST"
        request.state = {"completions_obj": AsyncMock()}
        request.state["completions_obj"].completions = AsyncMock(return_value=completions)
        return request

    def _build_payload(self, book="Genesis", chapter="1", collection_name="bsb"):
        payload = MagicMock()
        payload.book = book
        payload.chapter = chapter
        payload.collection_name = collection_name
        return payload

    def _patch_dependencies(self, **kwargs):
        defaults = {
            "async_read_file": AsyncMock(side_effect=["System prompt", "Quiz for {book} {chapter}: {verses}"]),
            "render_to_string": MagicMock(return_value="<html>Quiz</html>"),
            "ALL_VERSES": ALL_VERSES,
        }
        defaults.update(kwargs)
        return patch.multiple("ai.views.quiz_chapter", **defaults)

    def test_quiz_chapter_returns_rendered_quiz(self):
        request = self._build_request(json.dumps(_quiz_response()))
        payload = self._build_payload()

        render = MagicMock(return_value="<html>Quiz</html>")
        with self._patch_dependencies(render_to_string=render):
            response = self._call_view(request, payload)

        assert response.status_code == 200
        assert response["content-type"].startswith("text/html")
        assert response.content == b"<html>Quiz</html>"
        request.state["completions_obj"].completions.assert_called_once()
        render.assert_called_once_with("partials/server_quiz_partial.html", {"quiz_content": _quiz_response()})

    def test_quiz_chapter_passes_formatted_prompts_and_schema_to_llm(self):
        request = self._build_request(json.dumps(_quiz_response()))
        payload = self._build_payload(chapter="1")

        with self._patch_dependencies():
            self._call_view(request, payload)

        args = request.state["completions_obj"].completions.call_args.args
        assert args[0] == "System prompt"
        assert "Genesis" in args[1]
        assert "1" in args[1]
        assert "In the beginning" in args[1]
        assert args[2]["properties"]["quiz"]["minItems"] == 10
        assert args[2]["properties"]["quiz"]["maxItems"] == 10
        required = args[2]["properties"]["quiz"]["items"]["required"]
        assert "explanation" in required
        assert "verse_number" in required
        assert args[2]["properties"]["quiz"]["items"]["properties"]["verse_number"] == {"type": "integer"}

    def test_quiz_chapter_converts_chapter_to_int_for_verse_lookup(self):
        request = self._build_request(json.dumps(_quiz_response()))
        payload = self._build_payload(chapter="1")

        with self._patch_dependencies(ALL_VERSES={"bsb": {"Genesis": {1: {"1": "verse"}}}}):
            self._call_view(request, payload)

        request.state["completions_obj"].completions.assert_called_once()

    def test_quiz_chapter_attaches_book_chapter_and_verse_text(self):
        quiz = _quiz_response()
        for item in quiz["quiz"]:
            item.pop("book")
            item.pop("chapter")
            item.pop("verse_text")
        request = self._build_request(json.dumps(quiz))
        payload = self._build_payload()
        render = MagicMock(return_value="<html>Quiz</html>")

        with self._patch_dependencies(render_to_string=render):
            response = self._call_view(request, payload)

        assert response.status_code == 200
        rendered_quiz = render.call_args.args[1]["quiz_content"]
        assert all(item["book"] == "Genesis" for item in rendered_quiz["quiz"])
        assert all(item["chapter"] == "1" for item in rendered_quiz["quiz"])
        assert all(
            item["verse_text"] == "In the beginning God created the heavens and the earth."
            for item in rendered_quiz["quiz"]
        )

    def test_quiz_chapter_returns_error_when_verse_text_cannot_be_attached(self):
        quiz = _quiz_response()
        quiz["quiz"][0]["verse_number"] = 2
        request = self._build_request(json.dumps(quiz))
        payload = self._build_payload()

        with self._patch_dependencies():
            response = self._call_view(request, payload)

        self._assert_error(response, "Error attaching book name, chapter, or verse text")

    def _assert_error(self, response, message):
        assert response.status_code == 500
        assert response["content-type"].startswith("text/html")
        assert message.encode() in response.content

    def test_quiz_chapter_returns_error_when_verses_are_missing(self):
        request = self._build_request()
        payload = self._build_payload(book="Missing")

        with self._patch_dependencies():
            response = self._call_view(request, payload)

        self._assert_error(response, "Error locating verses")
        request.state["completions_obj"].completions.assert_not_called()

    def test_quiz_chapter_returns_error_when_prompt_loading_fails(self):
        request = self._build_request()
        payload = self._build_payload()

        with self._patch_dependencies(async_read_file=AsyncMock(side_effect=OSError("missing prompt"))):
            response = self._call_view(request, payload)

        self._assert_error(response, "Error formatting user prompt")

    def test_quiz_chapter_returns_error_when_prompts_cannot_be_stripped(self):
        request = self._build_request()
        payload = self._build_payload()
        read_file = AsyncMock(side_effect=[123, "Quiz {book} {chapter}: {verses}"])

        with self._patch_dependencies(async_read_file=read_file):
            response = self._call_view(request, payload)

        self._assert_error(response, "Error stripping whitespace")

    def test_quiz_chapter_returns_error_when_llm_fails(self):
        request = self._build_request()
        request.state["completions_obj"].completions = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        payload = self._build_payload()

        with self._patch_dependencies():
            response = self._call_view(request, payload)

        self._assert_error(response, "Error generating LLM response")

    def test_quiz_chapter_returns_error_for_invalid_json(self):
        for result, message in [
            ("not json", "Error unmarshalling LLM output"),
            ("[]", "Error attaching book name, chapter, or verse text"),
        ]:
            with self.subTest(result=result):
                request = self._build_request(result)
                payload = self._build_payload()

                with self._patch_dependencies():
                    response = self._call_view(request, payload)

                self._assert_error(response, message)

    def test_quiz_chapter_returns_error_for_invalid_quiz_structure(self):
        request = self._build_request(json.dumps({"quiz": []}))
        payload = self._build_payload()

        with self._patch_dependencies():
            response = self._call_view(request, payload)

        self._assert_error(response, "Error validating quiz content")

    def test_quiz_chapter_returns_error_when_template_rendering_fails(self):
        request = self._build_request(json.dumps(_quiz_response()))
        payload = self._build_payload()

        with self._patch_dependencies(render_to_string=MagicMock(side_effect=RuntimeError("template missing"))):
            response = self._call_view(request, payload)

        self._assert_error(response, "Error rendering template")

    def test_quiz_chapter_returns_error_when_output_validation_fails(self):
        request = self._build_request(json.dumps(_quiz_response()))
        payload = self._build_payload()
        output_serializer = MagicMock(side_effect=ValueError("invalid HTML"))

        with self._patch_dependencies(), patch("ai.views.quiz_chapter.ServerTextResponseSerializer", output_serializer):
            response = self._call_view(request, payload)

        self._assert_error(response, "Error validating output")

    @pytest.mark.asyncio
    async def test_quiz_chapter_rejects_invalid_payload_with_422(self):
        client = TestAsyncClient(router)

        response = await client.post(
            "/quiz_chapter",
            data={"book": "", "chapter": "1", "collection_name": "bsb"},
        )

        assert response.status_code == 422
