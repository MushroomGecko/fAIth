import os
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
import numpy as np
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class Embedding:
    """Docker Model Runner for embedding models."""
    def __init__(self):
        """Initialize the Docker Model Runner."""
        self.model_name = os.getenv("EMBEDDING_MODEL_ID", "Qwen/Qwen3-Embedding-0.6B")
        if not self.model_name:
            logger.error("Embedding model ID is not set")
            raise ValueError("Embedding model ID is not set")
        logger.info(f"Embedding model ID: {self.model_name}")

        embedding_url = os.getenv("EMBEDDING_URL", "http://localhost")
        embedding_port = os.getenv("EMBEDDING_PORT", "11435")
        base_url = f"{embedding_url}{':' if embedding_port else ''}{embedding_port}/v1"
        api_key = os.getenv("OPENAI_API_KEY", "sk-noauth")

        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.async_client = AsyncOpenAI(base_url=base_url, api_key=api_key)

        self.query_template = os.getenv("EMBEDDING_MODEL_QUERY_PROMPT", "")
        self.document_template = os.getenv("EMBEDDING_MODEL_DOCUMENT_PROMPT", "")

    def embedding_size(self):
        """Get the embedding size."""
        response = self.client.embeddings.create(model=self.model_name, input=["Hello, world!"])
        return len(response.data[0].embedding)

    def embed(self, batch: list[str], prompt_type: str = "document", normalize: bool = False):
        """Embed a batch of text."""
        # If the prompt type is query, we need to use the query template

        # Embed the batch
        embeddings = []
        if prompt_type == "query":
            batch_prompts = batch if self.query_template == "" else [self.query_template.format(text=text) for text in batch]
            response = self.client.embeddings.create(model=self.model_name, input=batch_prompts)
            embeddings = [item.embedding for item in response.data]
        # If the prompt type is document, we need to use the document template
        elif prompt_type == "document":
            batch_prompts = batch if self.document_template == "" else [self.document_template.format(text=text) for text in batch]
            response = self.client.embeddings.create(model=self.model_name, input=batch_prompts)
            embeddings = [item.embedding for item in response.data]
        # If the prompt type is unknown, raise an error
        else:
            raise ValueError(f"Unknown prompt type: {prompt_type}")

        # If not normalizing, return the embeddings
        if not normalize:
            return embeddings

        # Normalize the embeddings
        normalized = []
        for embedding in embeddings:
            array = np.asarray(embedding, dtype=np.float32)
            norm = np.linalg.norm(array)
            if norm > 0:
                array = array / norm
            normalized.append(array.tolist())

        # Return the normalized embeddings
        return normalized

    async def async_embed(self, batch: list[str], prompt_type: str = "document", normalize: bool = False):
        """Embed a batch of text."""
        # If the prompt type is query, we need to use the query template

        # Embed the batch
        embeddings = []
        if prompt_type == "query":
            batch_prompts = batch if self.query_template == "" else [self.query_template.format(text=text) for text in batch]
            response = await self.async_client.embeddings.create(model=self.model_name, input=batch_prompts)
            embeddings = [item.embedding for item in response.data]
        # If the prompt type is document, we need to use the document template
        elif prompt_type == "document":
            batch_prompts = batch if self.document_template == "" else [self.document_template.format(text=text) for text in batch]
            response = await self.async_client.embeddings.create(model=self.model_name, input=batch_prompts)
            embeddings = [item.embedding for item in response.data]
        # If the prompt type is unknown, raise an error
        else:
            raise ValueError(f"Unknown prompt type: {prompt_type}")

        # If not normalizing, return the embeddings
        if not normalize:
            return embeddings

        # Normalize the embeddings
        normalized = []
        for embedding in embeddings:
            array = np.asarray(embedding, dtype=np.float32)
            norm = np.linalg.norm(array)
            if norm > 0:
                array = array / norm
            normalized.append(array.tolist())

        # Return the normalized embeddings
        return normalized
        