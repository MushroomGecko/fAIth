from dotenv import load_dotenv
import os
import torch
import gc
import numpy as np

# Load environment variables
load_dotenv()

class Embedding:
    """Embedding engine for embedding models."""
    def __init__(self):
        """Initialize the embedding engine."""
        self.runner_name = os.getenv("EMBEDDING_MODEL_RUNNER", None)
        self.model_id = os.getenv("EMBEDDING_MODEL_ID", None)
        self.model_repo = os.getenv("EMBEDDING_MODEL_REPO", None)
        self.runner_object = None

        if self.runner_name is None or self.model_id is None:
            raise ValueError("EMBEDDING_MODEL_RUNNER and EMBEDDING_MODEL_ID must be set")

        self._get_runner()
        print(f"Embedding engine initialized to {self.runner_name}")

    def _get_runner(self):
        """Get the latest active embedding model and return the runner."""
        if self.runner_name == "hf_sentence_transformers":
            from ai.embedding.embedding_runners.hf_sentence_transformers import EmbeddingRunner
            self.runner_object = EmbeddingRunner(self.model_id)
        elif self.runner_name == "llama_cpp":
            if self.model_repo is None:
                raise ValueError("EMBEDDING_MODEL_REPO must be set for llama_cpp_python")
            from ai.embedding.embedding_runners.llama_cpp_python import EmbeddingRunner
            self.runner_object = EmbeddingRunner(self.model_id, self.model_repo or "")
        elif self.runner_name == "ollama":
            from ai.embedding.embedding_runners.ollama import EmbeddingRunner
            self.runner_object = EmbeddingRunner(self.model_id)
        elif self.runner_name == "docker_model_runner":
            from ai.embedding.embedding_runners.docker_model_runner import EmbeddingRunner
            self.runner_object = EmbeddingRunner(self.model_id)
        else:
            raise ValueError(f"Unknown embedding runner: {self.runner_name}")

    def embed(self, batch: list[str], prompt_type: str = "document", normalize: bool = False):
        """Embed a batch of text."""
        print(f"Embedding batch of {len(batch)} texts with {self.model_id}")
        embeddings = list(self.runner_object.embed(batch, prompt_type))
        if not normalize:
            return embeddings

        normalized = []
        for embedding in embeddings:
            array = np.asarray(embedding, dtype=np.float32)
            norm = np.linalg.norm(array)
            if norm > 0:
                array = array / norm
            normalized.append(array.tolist())
        return normalized
    
    def embedding_size(self):
        """Return the embedding size."""
        return len(list(self.embed(batch=["Hello, world!"], prompt_type="document", normalize=False))[0])

    def kill(self):
        """Kill the embedding engine."""
        self.runner_object.kill()
        del self.runner_object
        self.runner_object = None
        torch.cuda.empty_cache()
        gc.collect()
        print(f"Killed embedding engine for {self.model_id}")