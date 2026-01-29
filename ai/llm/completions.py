import os
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
import gc
import numpy as np
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class Completions:
    """Docker Model Runner for LLM models."""
    def __init__(self):
        """Initialize the Docker Model Runner."""
        self.model_name = os.getenv("LLM_MODEL_ID", "unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M")
        if not self.model_name:
            logger.error("LLM model ID is not set")
            raise ValueError("LLM model ID is not set")
        logger.info(f"LLM model ID: {self.model_name}")

        llm_url = os.getenv("LLM_URL", "http://localhost")
        llm_port = os.getenv("LLM_PORT", "11436")
        base_url = f"{llm_url}{':' if llm_port else ''}{llm_port}/v1"
        api_key = os.getenv("OPENAI_API_KEY", "sk-noauth")

        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def completions(self, system_prompt: str, user_prompt: str, query: str):
        """Generate a completion for a prompt."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt.format(query=query)}
        ]
        response = await self.client.chat.completions.create(model=self.model_name, messages=messages)
        return response.choices[0].message.content

    async def close(self):
        """Close the asynchronous Completions object."""
        logger.info("Closing asynchronous Completions object")
        try:
            await self.client.close()
        except Exception as e:
            logger.error(f"Error closing asynchronous Completions object: {e}")
            pass
        