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
        self.model = SentenceTransformer(self.model_name, device=os.getenv("EMBEDDING_DEVICE", "cpu"))

        self.query_template = os.getenv("EMBEDDING_MODEL_QUERY_PROMPT", "")
        self.document_template = os.getenv("EMBEDDING_MODEL_DOCUMENT_PROMPT", "")

    def embed(self, batch: list[str], prompt_type: str = "document"):        
        """Embed a batch of text."""
        # If the prompt type is query, we need to use the query template
        if prompt_type == "query":
            # If the query template is empty, we need to use the default query template
            if self.query_template == "":
                # Try to use the default query template if available
                try:
                    return self.model.encode_query(batch).tolist()
                # If the query template is not available, fallback to basic encoding
                except Exception:
                    return self.model.encode(batch).tolist()
            # If the query template is not empty, use the query template
            else:
                # Format the query template with the text
                prompts = []
                for text in batch:
                    prompt = self.query_template.format(text=text)
                    prompts.append(prompt)
                return self.model.encode(prompts).tolist()
        elif prompt_type == "document":
            # If the document template is empty, we need to use the default document template
            if self.document_template == "":
                # Try to use the default document template if available
                try:
                    return self.model.encode_document(batch).tolist()
                # If the document template is not available, fallback to basic encoding
                except Exception:
                    return self.model.encode(batch).tolist()
            # If the document template is not empty, use the document template
            else:
                # Format the document template with the text
                prompts = []
                for text in batch:
                    prompt = self.document_template.format(text=text)
                    prompts.append(prompt)
                return self.model.encode(prompts).tolist()
        # If the prompt type is unknown, raise an error
        else:
            raise ValueError(f"Unknown prompt type: {prompt_type}")
    
    def kill(self):
        """Kill the Hugging Face Sentence Transformers runner."""
        del self.model
        torch.cuda.empty_cache()
        gc.collect()
        print(f"Killed Hugging Face Sentence Transformers runner for {self.model_name}")