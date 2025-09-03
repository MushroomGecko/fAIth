import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmbeddingRunner:
    def __init__(self, model_name: str):
        self.model_name = model_name.lower()
        base_url = os.getenv(
            "OPENAI_BASE_URL",
            "http://localhost:12434/engines/llama.cpp/v1",
        )
        api_key = os.getenv("OPENAI_API_KEY", "sk-noauth")
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def embed(self, batch: list[str]):
        for text in batch:
            yield list(self.client.embeddings.create(model=self.model_name, input=text).data[0].embedding)
        