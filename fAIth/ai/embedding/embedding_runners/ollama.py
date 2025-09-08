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

        self.query_template = os.getenv("EMBEDDING_MODEL_QUERY_PROMPT", "")
        self.document_template = os.getenv("EMBEDDING_MODEL_DOCUMENT_PROMPT", "")
        
        ollama_models = ollama.list()["models"]
        ollama_models = [item["model"] for item in ollama_models]
        if self.model_name not in ollama_models:
            try:
                ollama.pull(model=self.model_name)
            except Exception:
                raise Exception(f"Model {self.model_name} not found in Ollama")

    def embed(self, batch: list[str], prompt_type: str = "document"):
        """Embed a batch of text."""
        # If the prompt type is query, we need to use the query template
        if prompt_type == "query":
            # If the query template is empty, we need to use the default query template
            if self.query_template == "":
                for text in batch:
                    yield list(ollama.embed(model=self.model_name, input=text).get("embeddings")[0])
            # If the query template is not empty, use the query template
            else:
                for text in batch:
                    prompt = self.query_template.format(text=text)
                    yield list(ollama.embed(model=self.model_name, input=prompt).get("embeddings")[0])
        # If the prompt type is document, we need to use the document template
        elif prompt_type == "document":
            # If the document template is empty, we need to use the default document template
            if self.document_template == "":
                for text in batch:
                    yield list(ollama.embed(model=self.model_name, input=text).get("embeddings")[0])
            # If the document template is not empty, use the document template
            else:
                for text in batch:
                    prompt = self.document_template.format(text=text)
                    yield list(ollama.embed(model=self.model_name, input=prompt).get("embeddings")[0])
        # If the prompt type is unknown, raise an error
        else:
            raise ValueError(f"Unknown prompt type: {prompt_type}")

    def kill(self):
        """Kill the Ollama runner."""
        os.system(f"ollama stop {self.model_name}")
        print(f"Killed Ollama runner for {self.model_name}")