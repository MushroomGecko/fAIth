from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class EmbeddingRunner:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def embed(self, batch: list[str], prompt_type: str = "query"):
        model = SentenceTransformer(self.model_name, device=os.getenv("DEVICE", "cpu"))

        if prompt_type == "query":
            return model.encode(batch, prompt_name="query").tolist()
        else:
            return model.encode(batch).tolist()
