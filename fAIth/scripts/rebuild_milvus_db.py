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

if MILVUS_DATABASE_NAME not in client.list_databases():
    client.create_database(MILVUS_DATABASE_NAME)
    client.use_database(MILVUS_DATABASE_NAME)
else:
    client.use_database(MILVUS_DATABASE_NAME)
    for collection in client.list_collections():
        client.drop_collection(collection)

# Create a schema for the collection
print(f"Creating schema for {MILVUS_DATABASE_NAME}")
schema = CollectionSchema(
    fields=[
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_ENGINE.embedding_size()),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2048),
        FieldSchema(name="version", dtype=DataType.VARCHAR, max_length=8),
        FieldSchema(name="book", dtype=DataType.VARCHAR, max_length=32),
        FieldSchema(name="chapter", dtype=DataType.INT16),
        FieldSchema(name="verse", dtype=DataType.INT16),
    ],
    auto_id=True,
)

# Make the Index Params
index_params = MilvusClient.prepare_index_params()
index_params.add_index(
    field_name="embedding",
    index_type="HNSW",
    metric_type="COSINE",
    params={"M": 32, "efConstruction": 256},
    index_name="hnsw_embedding",
)

# Create the collection for each version
print(f"Creating collections for {VERSION_SELECTION}")
for version in VERSION_SELECTION:
    client.create_collection(collection_name=version, 
                             schema=schema)
    client.create_index(collection_name=version, 
                        index_params=index_params,
                        sync=True)
print(client.list_collections())

# Add things to the collections
# Get the Bible version
for version in VERSION_SELECTION[:1]:
    # Get the books in order
    for book in IN_ORDER_BOOKS[:1]:
        for chapter in range(1, CHAPTER_SELECTION[book] + 1):
            # Get the verses for the book and chapter
            with open(BIBLE_DATA_ROOT / version / book / f"{chapter}.json", "r", encoding="utf-8") as file:
                verse_numbers = []
                verse_texts = []
                # Load the JSON data
                json_data = json.load(file)
                # Add the verses to the collection
                for verse in json_data.keys():
                    if "header_" in verse:
                        continue
                    verse_numbers.append(int(verse))
                    verse_texts.append(json_data[verse])
                verse_embeddings = EMBEDDING_ENGINE.embed(verse_texts, prompt_type="document", normalize=False)

                data = []
                for verse_number, verse_text, verse_embedding in zip(verse_numbers, verse_texts, verse_embeddings):
                    data.append({"embedding": verse_embedding, 
                                 "text": verse_text, 
                                 "version": version, 
                                 "book": book, 
                                 "chapter": chapter, 
                                 "verse": verse_number})
                client.insert(collection_name=version, 
                              data=data)
                print(f"Added {book} {chapter} to {version} collection")

client.close()