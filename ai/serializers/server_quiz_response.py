import logging

from pydantic import BaseModel, field_validator

# Set up logging
logger = logging.getLogger(__name__)


class ServerQuizResponseSerializer(BaseModel):
    """
    Validate and serialize a quiz response from the LLM.

    Ensures the response contains a valid quiz structure before processing.

    Fields:
        quiz_content (dict): The quiz content from the LLM.
    """

    quiz_content: dict
    
    @field_validator("quiz_content")
    @classmethod
    def validate_quiz_content(cls, value: dict) -> dict:
        """
        Validate the structure and contents of the quiz response.

        Parameters:
            value (dict): The quiz content returned by the LLM.

        Returns:
            dict: The validated quiz content.

        Raises:
            ValueError: If the quiz content has an invalid structure.
        """
        if not value or not isinstance(value, dict):
            logger.error("Quiz content must be a non-empty dictionary")
            raise ValueError("Quiz content must be a non-empty dictionary")

        if "quiz" not in value:
            logger.error("Quiz content must contain a 'quiz' key")
            raise ValueError("Quiz content must contain a 'quiz' key")

        if not isinstance(value["quiz"], list):
            logger.error("The 'quiz' field must be a list")
            raise ValueError("The 'quiz' field must be a list")

        if len(value["quiz"]) != 10:
            logger.error("The 'quiz' field must contain exactly 10 items")
            raise ValueError("The 'quiz' field must contain exactly 10 items")

        for item in value["quiz"]:
            if not isinstance(item, dict):
                logger.error("Each quiz item must be a dictionary")
                raise ValueError("Each quiz item must be a dictionary")

            if "question" not in item:
                logger.error("Each quiz item must contain a 'question' key")
                raise ValueError("Each quiz item must contain a 'question' key")

            if not isinstance(item["question"], str):
                logger.error("Each question must be a string")
                raise ValueError("Each question must be a string")

            if item["question"].strip() == "":
                logger.error("Questions cannot be empty")
                raise ValueError("Questions cannot be empty")

            if "options" not in item:
                logger.error("Each quiz item must contain an 'options' key")
                raise ValueError("Each quiz item must contain an 'options' key")

            if not isinstance(item["options"], dict):
                logger.error("Quiz options must be a dictionary")
                raise ValueError("Quiz options must be a dictionary")

            if len(item["options"]) != 4:
                logger.error("Quiz options must contain exactly four entries")
                raise ValueError("Quiz options must contain exactly four entries")

            expected_options = {"a", "b", "c", "d"}
            if set(item["options"]) != expected_options:
                logger.error("Quiz options must use exactly the keys 'a', 'b', 'c', and 'd'")
                raise ValueError("Quiz options must use exactly the keys 'a', 'b', 'c', and 'd'")

            for option in item["options"].values():
                if not isinstance(option, str):
                    logger.error("Each quiz option must be a string")
                    raise ValueError("Each quiz option must be a string")
                if not option.strip():
                    logger.error("Quiz options cannot be empty")
                    raise ValueError("Quiz options cannot be empty")

            if "answer" not in item:
                logger.error("Each quiz item must contain an 'answer' key")
                raise ValueError("Each quiz item must contain an 'answer' key")

            if not isinstance(item["answer"], str):
                logger.error("Each answer key must be a string")
                raise ValueError("Each answer key must be a string")

            if item["answer"] not in item["options"]:
                logger.error("Each answer key must match one of the quiz option keys")
                raise ValueError("Each answer key must match one of the quiz option keys")

        return value
