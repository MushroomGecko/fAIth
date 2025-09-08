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

        self.query_template = os.getenv("EMBEDDING_MODEL_QUERY_PROMPT", "")
        self.document_template = os.getenv("EMBEDDING_MODEL_DOCUMENT_PROMPT", "")

    def embed(self, batch: list[str], prompt_type: str = "document"):
        """Embed a batch of text."""
        # If the prompt type is query, we need to use the query template
        if prompt_type == "query":
            # If the query template is empty, we need to use the default query template
            if self.query_template == "":
                for text in batch:
                    yield list(self.client.embeddings.create(model=self.model_name, input=text).data[0].embedding)
            else:
                for text in batch:
                    prompt = self.query_template.format(text=text)
                    yield list(self.client.embeddings.create(model=self.model_name, input=prompt).data[0].embedding)
        # If the prompt type is document, we need to use the document template
        elif prompt_type == "document":
            # If the document template is empty, we need to use the default document template
            if self.document_template == "":
                for text in batch:
                    yield list(self.client.embeddings.create(model=self.model_name, input=text).data[0].embedding)
            else:
                for text in batch:
                    prompt = self.document_template.format(text=text)
                    yield list(self.client.embeddings.create(model=self.model_name, input=prompt).data[0].embedding)
        # If the prompt type is unknown, raise an error
        else:
            raise ValueError(f"Unknown prompt type: {prompt_type}")

    def kill(self):
        """Kill the Docker Model Runner."""
        if self.client:
            self.client.close()
        del self.client
        self.client = None
        gc.collect()
        print(f"Killed Docker Model Runner for {self.model_name}")
        