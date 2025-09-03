import ollama
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmbeddingRunner:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def embed(self, batch: list[str]):
        ollama_models = ollama.list()["models"]
        ollama_models = [item["model"] for item in ollama_models]
        if self.model_name not in ollama_models:
            try:
                ollama.pull(model=self.model_name)
            except Exception:
                raise Exception(f"Model {self.model_name} not found in Ollama")
        for text in batch:
            yield list(ollama.embed(model=self.model_name, input=text).get("embeddings")[0])