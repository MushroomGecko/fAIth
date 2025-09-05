import os
from openai import OpenAI
from dotenv import load_dotenv
import gc

# Load environment variables
load_dotenv()

class EmbeddingRunner:
    """Docker Model Runner for embedding models."""
    def __init__(self, model_name: str):
        """Initialize the Docker Model Runner."""
        self.model_name = model_name.lower()
        base_url = os.getenv(
            "OPENAI_BASE_URL",
            "http://localhost:12434/engines/llama.cpp/v1",
        )
        api_key = os.getenv("OPENAI_API_KEY", "sk-noauth")
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def embed(self, batch: list[str], prompt_type: str = "document"):
        """Embed a batch of text."""
        for text in batch:
            yield list(self.client.embeddings.create(model=self.model_name, input=text).data[0].embedding)

    def kill(self):
        """Kill the Docker Model Runner."""
        if self.client:
            self.client.close()
        del self.client
        self.client = None
        gc.collect()
        print(f"Killed Docker Model Runner for {self.model_name}")
        