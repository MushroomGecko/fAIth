from pymilvus import MilvusClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


class VectorDatabase:
    """Milvus standalone client."""
    def __init__(self):
        """Initialize the Milvus standalone client."""
        MILVUS_URL = os.getenv("MILVUS_URL")
        MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME")
        MILVUS_USERNAME = os.getenv("MILVUS_USERNAME")
        MILVUS_PASSWORD = os.getenv("MILVUS_PASSWORD")

        self.client = MilvusClient()

    def create_collection(self, collection_name: str):
        """Create a collection."""
        self.client.create_collection(collection_name)