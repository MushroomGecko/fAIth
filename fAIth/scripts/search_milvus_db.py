from pathlib import Path
import sys
import os
from pymilvus import MilvusClient, CollectionSchema, FieldSchema, DataType
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

MILVUS_URL = os.getenv("MILVUS_URL")
MILVUS_DATABASE_NAME = os.getenv("MILVUS_DATABASE_NAME")
MILVUS_USERNAME = os.getenv("MILVUS_USERNAME")
MILVUS_PASSWORD = os.getenv("MILVUS_PASSWORD")

# Make sure we can import the Django project without initializing apps
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fAIth.settings")
from frontend.globals import BIBLE_DATA_ROOT, VERSION_SELECTION, IN_ORDER_BOOKS, CHAPTER_SELECTION
from ai.globals import EMBEDDING_ENGINE

# Establish a connection to the Milvus database
client = MilvusClient(uri=MILVUS_URL,
                      token=f"{MILVUS_USERNAME}:{MILVUS_PASSWORD}")

if MILVUS_DATABASE_NAME in client.list_databases():
    client.use_database(MILVUS_DATABASE_NAME)
else:
    print(f"Database {MILVUS_DATABASE_NAME} not found")
    exit(1)

# Test the search
sample_queries = ["In the beginning", "Sodom and Gomorrah", "Garden of Eden", "Tower of Babel", "Adam and Eve"]
collection_name = "bsb"
limit = 5

query_embeddings = EMBEDDING_ENGINE.embed(sample_queries, prompt_type="query", normalize=False)
client.load_collection(collection_name=collection_name)
for i, query_embedding in enumerate(query_embeddings):
    results = client.search(
        collection_name=collection_name,
        data=[query_embedding],
        limit=limit,
        search_params={"metric_type": "COSINE", "params": {"ef": 128}}, # Dense embedding
        output_fields=["version", "book", "chapter", "verse", "text"],
    )
    # Dense results
    print("\n########################")
    print(f"Results for {sample_queries[i]}:")
    for i, result in enumerate(results[0]):
        print(
            f"{i+1}. Score: {result['distance']:.4f}, Content: {result['entity']['text']}"
        )