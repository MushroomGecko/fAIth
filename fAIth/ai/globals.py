from django.utils.functional import SimpleLazyObject

def get_embedding_engine():
    """Get the embedding engine."""
    from ai.embedding.embedding import Embedding
    try:
        print("Getting embedding engine")
        return Embedding()
    except Exception as e:
        print(f"Error getting embedding engine {e}")
        return None

EMBEDDING_ENGINE = SimpleLazyObject(get_embedding_engine)
