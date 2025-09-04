from ai.models.embedding import EmbeddingModel


class Embedding:
    """Embedding engine for embedding models."""
    def __init__(self):
        """Initialize the embedding engine."""
        self.runner = None
        self.model_slug = None

        self._get_runner()
        print(f"Embedding engine initialized to {self.model_slug}")
        print(f"Active embedding models: {EmbeddingModel.objects.list_active()}")

    def _get_runner(self):
        """Get the latest active embedding model and return the runner."""
        model = EmbeddingModel.objects.get_latest_active()
        if model is None:
            raise RuntimeError("No active embedding model found")
        
        self.model_slug = model.slug

        if model.runner == "hf_sentence_transformers":
            from ai.embedding.runners.hf_sentence_transformers import EmbeddingRunner
            self.runner = EmbeddingRunner(model.model_id)
        elif model.runner == "llama_cpp_python":
            from ai.embedding.runners.llama_cpp_python import EmbeddingRunner
            self.runner = EmbeddingRunner(model.model_id, model.model_repo or "")
        elif model.runner == "ollama":
            from ai.embedding.runners.ollama import EmbeddingRunner
            self.runner = EmbeddingRunner(model.model_id)
        elif model.runner == "docker_model_runner":
            from ai.embedding.runners.docker_model_runner import EmbeddingRunner
            self.runner = EmbeddingRunner(model.model_id)
        else:
            raise ValueError(f"Unknown embedding runner: {model.runner}")

    def embed(self, batch: list[str], prompt_type: str = "query"):
        """Embed a batch of text."""
        print(f"Embedding batch of {len(batch)} texts with {self.model_slug}")
        return list(self.runner.embed(batch, prompt_type))

    def kill(self):
        """Kill the embedding engine."""
        self.runner.kill()