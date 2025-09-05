import ollama
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class EmbeddingRunner:
    """Ollama runner for embedding models."""
    def __init__(self, model_name: str):
        """Initialize the Ollama runner."""
        self.model_name = model_name
        
        ollama_models = ollama.list()["models"]
        ollama_models = [item["model"] for item in ollama_models]
        if self.model_name not in ollama_models:
            try:
                ollama.pull(model=self.model_name)
            except Exception:
                raise Exception(f"Model {self.model_name} not found in Ollama")

    def embed(self, batch: list[str], prompt_type: str = "document"):
        """Embed a batch of text."""
        for text in batch:
            yield list(ollama.embed(model=self.model_name, input=text).get("embeddings")[0])

    def kill(self):
        """Kill the Ollama runner."""
        os.system(f"ollama stop {self.model_name}")
        print(f"Killed Ollama runner for {self.model_name}")