# !pip install llama-cpp-python

from llama_cpp import Llama
from dotenv import load_dotenv
import os
import gc

# Load environment variables
load_dotenv()

class EmbeddingRunner:
    """Llama CPP Python runner for embedding models."""
    def __init__(self, model_name: str, model_repo: str):
        """Initialize the Llama CPP Python runner."""
        self.model_name = model_name
        self.model_repo = model_repo
        self.llm = None

        candidate_layers = []
        if os.getenv("EMBEDDING_DEVICE") == "cuda":
            layers_to_try = int(os.getenv("EMBEDDING_GPU_LAYERS"))
            # We want to try the highest number of layers that is a power of 2
            if layers_to_try >= 1:
                # We start with -1 because that's the default (Use all layers)
                candidate_layers = [-1]
                n = layers_to_try
                # Get exponentially decreasing numbers of layers
                while n >= 1:
                    candidate_layers.append(n)
                    n //= 2
                candidate_layers.append(0)
            # User may want to use the CPU here and GPU somewhere else
            elif layers_to_try == 0:
                candidate_layers = [0]
            # Try all layers or bust
            elif layers_to_try > 0:
                candidate_layers = [-1, 0]
        elif os.getenv("EMBEDDING_DEVICE") == "cpu":
            candidate_layers = [0]
        else:
            raise ValueError(f"Unknown device: {os.getenv('EMBEDDING_DEVICE')}")

        # Try to load the model with different numbers of layers until it succeeds (very hacky, but hey, Llama CPP Python doesn't auto-offload layers like Ollama)
        for layer in candidate_layers:
            try:
                print(f"Trying to load Llama CPP Python model with {layer} layers")
                self.llm = Llama.from_pretrained(
                    filename=self.model_name,
                    repo_id=self.model_repo,
                    embedding=True,
                    n_ctx=0,
                    n_gpu_layers=layer,
                    verbose=False,
                )
                break
            except Exception:
                if self.llm is not None:
                    self.llm.close()
                del self.llm
                self.llm = None
                continue
        if self.llm is None:
            raise ValueError(f"No Llama CPP Python model found for {self.model_name}")

    def embed(self, batch: list[str], prompt_type: str = "document"):
        """Embed a batch of text."""
        for text in batch:
            yield list(self.llm.create_embedding(input=text).get("data")[0].get("embedding"))


    def kill(self):
        """Kill the Llama CPP Python runner."""
        if self.llm is not None:
            self.llm.close()
        del self.llm
        self.llm = None
        gc.collect()
        print(f"Killed Llama CPP Python runner for {self.model_name}")