import json
import logging
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class Completions:
    """
    Asynchronous client for generating LLM completions using an OpenAI-compatible API.

    Handles chat-based completions with system and user prompts. Designed for use with
    Django's lifespan manager to manage the async client lifecycle.

    Configuration from environment variables:
        - LLM_MODEL_ID: Model identifier (default: "unsloth/Qwen3.5-4B-GGUF:Q4_K_M")
        - LLM_URL, LLM_PORT: Service endpoint (default: http://localhost:11436)
        - LLM_MODEL_ARGUMENTS: JSON string of model-specific parameters (default: {} for compatibility with other models that may not share the same parameters)
        - OPENAI_API_KEY: Authentication key (default: "sk-noauth")
    """

    def __init__(self):
        """
        Initialize the LLM completions client and validate configuration.

        Loads model configuration from environment variables and establishes
        an async connection to the LLM service.

        Raises:
            ValueError: If LLM_MODEL_ID is not set.
        """
        # Load and validate LLM model configuration
        self.model_name = str(os.getenv("LLM_MODEL_ID", "unsloth/Qwen3.5-4B-GGUF:Q4_K_M")).strip()
        if not self.model_name:
            logger.error("LLM model ID is not set")
            raise ValueError("LLM model ID is not set")
        logger.info(f"LLM model ID: {self.model_name}")

        # Load optional model-specific parameters (e.g., temperature, top_p, enable_thinking, etc.)
        self.model_arguments = json.loads(str(os.getenv("LLM_MODEL_ARGUMENTS", "{}")).strip())
        if not self.model_arguments:
            logger.warning("LLM model arguments are not set")
            self.model_arguments = {}
        logger.info(f"LLM model arguments: {self.model_arguments}")

        # Build service endpoint URL and authentication
        llm_url = str(os.getenv("LLM_URL", "http://localhost")).strip()
        llm_port = str(os.getenv("LLM_PORT", "11436")).strip()
        base_url = f"{llm_url}{':' if llm_port else ''}{llm_port}/v1"
        api_key = str(os.getenv("OPENAI_API_KEY", "sk-noauth")).strip()

        # Initialize async OpenAI-compatible client
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def completions(self, system_prompt: str, user_prompt: str, query: str):
        """
        Generate an LLM completion asynchronously.

        Sends a chat completion request with system context and user query.
        The user_prompt can contain a {query} placeholder that will be formatted.

        Parameters:
            system_prompt (str): System message defining the LLM's role and behavior.
            user_prompt (str): User message template, may contain {query} placeholder.
            query (str): The actual query to format into user_prompt.

        Returns:
            str: Generated completion text from the LLM.

        Raises:
            Exception: If the LLM service is unavailable or request fails.
        """
        # Build message list: system instruction followed by user query
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt.format(query=query)}
        ]
        
        # Request completion from LLM with model-specific parameters
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            extra_body=self.model_arguments
        )
        
        # Extract and return the generated text
        return response.choices[0].message.content

    async def close(self):
        """
        Close the async LLM client connection gracefully.

        Ensures proper cleanup during application shutdown. Errors during
        close are logged but don't raise exceptions.
        """
        logger.info("Closing asynchronous Completions object")
        try:
            await self.client.close()
        except Exception as e:
            logger.error(f"Error closing asynchronous Completions object: {e}")
            pass