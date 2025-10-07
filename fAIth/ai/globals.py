from django.utils.functional import SimpleLazyObject
import os

def get_embedding_engine():
    """Get the embedding engine."""
    from ai.vdb.embedding import Embedding
    try:
        print("Getting embedding engine")
        return Embedding(model_name=os.getenv("EMBEDDING_MODEL_ID", ""))
    except Exception as e:
        print(f"Error getting embedding engine {e}")
        return None

EMBEDDING_ENGINE = SimpleLazyObject(get_embedding_engine)
