import logging
import os

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class Embedding:
    """
    Client for generating text embeddings using a remote embedding model.

    Provides both synchronous and asynchronous methods for embedding text into vectors.
    Supports prompt templates for query and document embeddings separately, which can
    optimize embeddings for search vs. indexing tasks.

    The client communicates with an OpenAI-compatible embedding service (e.g., Docker container).

    Configuration from environment variables:
        - EMBEDDING_MODEL_ID: Model identifier (default: "Qwen/Qwen3-Embedding-0.6B")
        - EMBEDDING_URL, EMBEDDING_PORT: Service endpoint
        - OPENAI_API_KEY: Authentication key
        - EMBEDDING_MODEL_QUERY_PROMPT: Template for query embeddings (optional)
        - EMBEDDING_MODEL_DOCUMENT_PROMPT: Template for document embeddings (optional)
    """

    def __init__(self):
        """
        Initialize the embedding client and establish connection to the embedding service.

        Loads configuration from environment variables and creates both sync and async clients.
        The embedding model ID must be set; raises ValueError if not provided.

        Raises:
            ValueError: If EMBEDDING_MODEL_ID is not set.
        """
        # Load and validate embedding model configuration
        self.model_name = str(os.getenv("EMBEDDING_MODEL_ID", "Qwen/Qwen3-Embedding-0.6B")).strip()
        if not self.model_name:
            logger.error("Embedding model ID is not set")
            raise ValueError("Embedding model ID is not set")
        logger.info(f"Embedding model ID: {self.model_name}")

        # Build service endpoint URL
        embedding_url = str(os.getenv("EMBEDDING_URL", "http://localhost")).strip()
        embedding_port = str(os.getenv("EMBEDDING_PORT", "11435")).strip()
        base_url = f"{embedding_url}{':' if embedding_port else ''}{embedding_port}/v1"
        api_key = str(os.getenv("OPENAI_API_KEY", "sk-noauth")).strip()

        # Initialize both sync and async clients for OpenAI-compatible API
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.async_client = AsyncOpenAI(base_url=base_url, api_key=api_key)

        # Load optional prompt templates for specialized embeddings
        self.query_template = str(os.getenv("EMBEDDING_MODEL_QUERY_PROMPT", "")).strip()
        self.document_template = str(os.getenv("EMBEDDING_MODEL_DOCUMENT_PROMPT", "")).strip()

    def embedding_size(self):
        """
        Get the dimensionality of embeddings from the model.

        Makes a test embedding request to determine vector size.

        Returns:
            int: Embedding dimension (e.g., 256, 768, 1024).
        """
        response = self.client.embeddings.create(model=self.model_name, input=["Hello, world!"])
        return len(response.data[0].embedding)

    def embed(self, batch: list[str], prompt_type: str = "document", normalize: bool = False):
        """
        Generate embeddings for a batch of texts synchronously.

        Used primarily during vector database building for batch processing large volumes.
        Applies prompt templates if configured to optimize embeddings for search vs. indexing.

        Parameters:
            batch (list[str]): List of text strings to embed.
            prompt_type (str): Type of text - "document" (default) or "query".
                - "document": Text from documents being indexed (uses EMBEDDING_MODEL_DOCUMENT_PROMPT)
                - "query": User search queries (uses EMBEDDING_MODEL_QUERY_PROMPT)
            normalize (bool): If True, L2-normalizes embeddings to unit vectors (default: False).

        Returns:
            list: List of embedding vectors (each is a list of floats).

        Raises:
            ValueError: If prompt_type is not "document" or "query".
        """
        # Prepare prompts by applying template if configured
        embeddings = []
        
        if prompt_type == "query":
            # Apply query template if available, else use text as-is
            batch_prompts = batch if self.query_template == "" else [self.query_template.format(text=text) for text in batch]
            response = self.client.embeddings.create(model=self.model_name, input=batch_prompts)
            embeddings = [item.embedding for item in response.data]
        elif prompt_type == "document":
            # Apply document template if available, else use text as-is
            batch_prompts = batch if self.document_template == "" else [self.document_template.format(text=text) for text in batch]
            response = self.client.embeddings.create(model=self.model_name, input=batch_prompts)
            embeddings = [item.embedding for item in response.data]
        else:
            raise ValueError(f"Unknown prompt type: {prompt_type}")

        # Skip normalization if not requested
        if not normalize:
            return embeddings

        # L2-normalize embeddings to unit length vectors
        normalized = []
        for embedding in embeddings:
            array = np.asarray(embedding, dtype=np.float32)
            norm = np.linalg.norm(array)
            if norm > 0:
                array = array / norm
            normalized.append(array.tolist())

        return normalized

    async def async_embed(self, batch: list[str], prompt_type: str = "document", normalize: bool = False):
        """
        Generate embeddings for a batch of texts asynchronously.

        Used during query time and other async operations to avoid blocking the event loop.
        Applies prompt templates if configured to optimize embeddings for search vs. indexing.

        Parameters:
            batch (list[str]): List of text strings to embed.
            prompt_type (str): Type of text - "document" (default) or "query".
                - "document": Text from documents being indexed (uses EMBEDDING_MODEL_DOCUMENT_PROMPT)
                - "query": User search queries (uses EMBEDDING_MODEL_QUERY_PROMPT)
            normalize (bool): If True, L2-normalizes embeddings to unit vectors (default: False).

        Returns:
            list: List of embedding vectors (each is a list of floats).

        Raises:
            ValueError: If prompt_type is not "document" or "query".
        """
        # Prepare prompts by applying template if configured
        embeddings = []
        
        if prompt_type == "query":
            # Apply query template if available, else use text as-is
            batch_prompts = batch if self.query_template == "" else [self.query_template.format(text=text) for text in batch]
            response = await self.async_client.embeddings.create(model=self.model_name, input=batch_prompts)
            embeddings = [item.embedding for item in response.data]
        elif prompt_type == "document":
            # Apply document template if available, else use text as-is
            batch_prompts = batch if self.document_template == "" else [self.document_template.format(text=text) for text in batch]
            response = await self.async_client.embeddings.create(model=self.model_name, input=batch_prompts)
            embeddings = [item.embedding for item in response.data]
        else:
            raise ValueError(f"Unknown prompt type: {prompt_type}")

        # Skip normalization if not requested
        if not normalize:
            return embeddings

        # L2-normalize embeddings to unit length vectors
        normalized = []
        for embedding in embeddings:
            array = np.asarray(embedding, dtype=np.float32)
            norm = np.linalg.norm(array)
            if norm > 0:
                array = array / norm
            normalized.append(array.tolist())

        return normalized