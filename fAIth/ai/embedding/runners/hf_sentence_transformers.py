from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os
import torch
import gc

# Load environment variables
load_dotenv()

class EmbeddingRunner:
    """Hugging Face Sentence Transformers runner for embedding models."""
    def __init__(self, model_name: str):
        """Initialize the Hugging Face Sentence Transformers runner."""
        self.model_name = model_name
        self.model = SentenceTransformer(self.model_name, 
                                         device=os.getenv("DEVICE", "cpu"))

    def embed(self, batch: list[str], prompt_type: str = "query"):        
        """Embed a batch of text."""
        if prompt_type == "query":
            return self.model.encode(batch, prompt_name="query").tolist()
        else:
            return self.model.encode(batch).tolist()

    def kill(self):
        """Kill the Hugging Face Sentence Transformers runner."""
        del self.model
        torch.cuda.empty_cache()
        gc.collect()
        print(f"Killed Hugging Face Sentence Transformers runner for {self.model_name}")