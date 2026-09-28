"""Tests for the ServerQuizResponseSerializer."""

import copy

import pytest
from pydantic import ValidationError

from ai.serializers.server_quiz_response import ServerQuizResponseSerializer


def _quiz_item(**overrides):
    item = {
        "question": "What was created in the beginning?",
        "options": {"a": "Light", "b": "Water", "c": "Land", "d": "Life"},
        "answer": "a",
    }
    item.update(overrides)
    return item


def _valid_content():
    return {"quiz": [_quiz_item() for _ in range(10)]}


class TestServerQuizResponseSerializer:
    def test_valid_quiz_response(self):
        content = _valid_content()

        serializer = ServerQuizResponseSerializer(quiz_content=content)

        assert serializer.quiz_content == content

    @pytest.mark.parametrize("value", [{}])
    def test_quiz_content_must_be_a_non_empty_dictionary(self, value):
        with pytest.raises(ValidationError, match="non-empty dictionary"):
            ServerQuizResponseSerializer(quiz_content=value)

    @pytest.mark.parametrize("value", [None, [], "quiz"])
    def test_quiz_content_must_have_dictionary_type(self, value):
        with pytest.raises(ValidationError):
            ServerQuizResponseSerializer(quiz_content=value)

    def test_quiz_key_is_required(self):
        with pytest.raises(ValidationError, match="'quiz' key"):
            ServerQuizResponseSerializer(quiz_content={"questions": []})

    @pytest.mark.parametrize("value", [None, {}, "quiz", 10])
    def test_quiz_must_be_a_list(self, value):
        with pytest.raises(ValidationError, match="'quiz' field must be a list"):
            ServerQuizResponseSerializer(quiz_content={"quiz": value})

    @pytest.mark.parametrize("count", [0, 9, 11])
    def test_quiz_must_contain_exactly_ten_items(self, count):
        content = {"quiz": [_quiz_item() for _ in range(count)]}

        with pytest.raises(ValidationError, match="exactly 10 items"):
            ServerQuizResponseSerializer(quiz_content=content)

    @pytest.mark.parametrize(
        ("mutator", "message"),
        [
            (lambda item: item.update(question=None), "question must be a string"),
            (lambda item: item.update(question="   "), "Questions cannot be empty"),
            (lambda item: item.pop("question"), "'question' key"),
            (lambda item: item.update(options=None), "options must be a dictionary"),
            (lambda item: item.pop("options"), "'options' key"),
            (lambda item: item.update(answer=None), "answer key must be a string"),
            (lambda item: item.pop("answer"), "'answer' key"),
            (lambda item: item.update(answer="x"), "match one of the quiz option keys"),
        ],
    )
    def test_quiz_item_fields_are_validated(self, mutator, message):
        content = _valid_content()
        mutator(content["quiz"][0])

        with pytest.raises(ValidationError, match=message):
            ServerQuizResponseSerializer(quiz_content=content)

    @pytest.mark.parametrize(
        ("options", "message"),
        [
            ({"a": "1", "b": "2", "c": "3"}, "exactly four entries"),
            ({"a": "1", "b": "2", "c": "3", "x": "4"}, "exactly the keys"),
            ({"a": "1", "b": "2", "c": "3", "d": None}, "option must be a string"),
            ({"a": "1", "b": "2", "c": "3", "d": "   "}, "options cannot be empty"),
        ],
    )
    def test_options_are_four_non_empty_strings_with_expected_keys(self, options, message):
        content = _valid_content()
        content["quiz"][0]["options"] = options

        with pytest.raises(ValidationError, match=message):
            ServerQuizResponseSerializer(quiz_content=content)

    def test_each_quiz_item_must_be_a_dictionary(self):
        content = _valid_content()
        content["quiz"][0] = "not an item"

        with pytest.raises(ValidationError, match="item must be a dictionary"):
            ServerQuizResponseSerializer(quiz_content=content)

    def test_missing_quiz_content_is_rejected(self):
        with pytest.raises(ValidationError):
            ServerQuizResponseSerializer()  # type: ignore[call-arg]

    def test_validation_does_not_mutate_input(self):
        content = _valid_content()
        original = copy.deepcopy(content)

        ServerQuizResponseSerializer(quiz_content=content)

        assert content == original
