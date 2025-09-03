# !pip install llama-cpp-python

from llama_cpp import Llama
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmbeddingRunner:
    def __init__(self, model_name: str, model_repo: str):
        self.model_name = model_name
        self.model_repo = model_repo

    def embed(self, batch: list[str]):
        llm = Llama.from_pretrained(
            filename=self.model_name,
            repo_id=self.model_repo,
            embedding=True,
            verbose=False,
        )
        for text in batch:
            yield list(llm.create_embedding(input=text).get("data")[0].get("embedding"))
