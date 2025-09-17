from pathlib import Path
import sys
import os
from pymilvus import MilvusClient, CollectionSchema, FieldSchema, DataType, Function, FunctionType, AnnSearchRequest, WeightedRanker
from dotenv import load_dotenv
import json
from frontend.globals import BIBLE_DATA_ROOT, VERSION_SELECTION, IN_ORDER_BOOKS, CHAPTER_SELECTION
from ai.globals import EMBEDDING_ENGINE

# Load environment variables
load_dotenv()


class VectorDatabase:
    """Milvus standalone client."""
    def __init__(self):
        """Initialize the Milvus standalone client."""

        # Get Milvus connection information
        self.milvus_url = os.getenv("MILVUS_URL")
        self.milvus_port = os.getenv("MILVUS_PORT")
        self.milvus_database_name = os.getenv("MILVUS_DATABASE_NAME")
        self.milvus_username = os.getenv("MILVUS_USERNAME")
        self.milvus_password = os.getenv("MILVUS_PASSWORD")

        # Get the database type
        self.database_type = os.getenv("DATABASE_TYPE", "hybrid")

        # Establish a connection to the Milvus database
        self.client = MilvusClient(uri=f"{self.milvus_url}{':' if self.milvus_port else ''}{self.milvus_port}", token=f"{self.milvus_username}:{self.milvus_password}")

        # Build the database if it doesn't exist
        if self.milvus_database_name not in self.client.list_databases():
            self.build_database()
        # Use the database if it exists and load the collections
        else:
            self.client.use_database(self.milvus_database_name)
            for collection in self.client.list_collections():
                self.client.load_collection(collection_name=collection)

    def build_database(self):
        # Rebuild the database
        if self.milvus_database_name not in self.client.list_databases():
            self.client.create_database(self.milvus_database_name)
            self.client.use_database(self.milvus_database_name)
        else:
            self.client.use_database(self.milvus_database_name)
            for collection in self.client.list_collections():
                self.client.drop_collection(collection)

        # Create a schema for the collection
        print(f"Creating schema for {self.milvus_database_name}")
        # Sparse database
        if self.database_type == "sparse":
            schema = CollectionSchema(
                fields=[
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
                    FieldSchema(name="sparse_embedding", dtype=DataType.SPARSE_FLOAT_VECTOR),
                    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2048, enable_analyzer=True),
                    FieldSchema(name="version", dtype=DataType.VARCHAR, max_length=8),
                    FieldSchema(name="book", dtype=DataType.VARCHAR, max_length=32),
                    FieldSchema(name="chapter", dtype=DataType.INT16),
                    FieldSchema(name="verse", dtype=DataType.INT16),
                ],
                auto_id=True,
            )
        # Dense database
        elif self.database_type == "dense":
            schema = CollectionSchema(
                fields=[
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
                    FieldSchema(name="dense_embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_ENGINE.embedding_size()),
                    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2048, enable_analyzer=True),
                    FieldSchema(name="version", dtype=DataType.VARCHAR, max_length=8),
                    FieldSchema(name="book", dtype=DataType.VARCHAR, max_length=32),
                    FieldSchema(name="chapter", dtype=DataType.INT16),
                    FieldSchema(name="verse", dtype=DataType.INT16),
                ],
                auto_id=True,
            )
        # Hybrid database
        elif self.database_type == "hybrid":
            schema = CollectionSchema(
                fields=[
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
                    FieldSchema(name="dense_embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_ENGINE.embedding_size()),
                    FieldSchema(name="sparse_embedding", dtype=DataType.SPARSE_FLOAT_VECTOR),
                    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2048, enable_analyzer=True),
                    FieldSchema(name="version", dtype=DataType.VARCHAR, max_length=8),
                    FieldSchema(name="book", dtype=DataType.VARCHAR, max_length=32),
                    FieldSchema(name="chapter", dtype=DataType.INT16),
                    FieldSchema(name="verse", dtype=DataType.INT16),
                ],
                auto_id=True,
            )

        # Make the Index Params
        index_params = MilvusClient.prepare_index_params()

        # Sparse embedding
        if self.database_type == "sparse" or self.database_type == "hybrid":
            bm25_function = Function(
                name="text_bm25_emb", # Function name
                input_field_names=["text"], # Name of the VARCHAR field containing raw text data
                output_field_names=["sparse_embedding"], # Name of the SPARSE_FLOAT_VECTOR field reserved to store generated embeddings
                function_type=FunctionType.BM25, # Set to `BM25`
            )
            schema.add_function(bm25_function)
            # Sparse embedding
            index_params.add_index(
            field_name="sparse_embedding",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="BM25",
            params={
                "inverted_index_algo": "DAAT_MAXSCORE",
                "bm25_k1": 1.2,
                "bm25_b": 0.75}
            )
        # Dense embedding
        if self.database_type == "dense" or self.database_type == "hybrid":
            # Dense embedding
            index_params.add_index(
                field_name="dense_embedding",
                index_type="HNSW",
                metric_type="COSINE",
                params={"M": 32, "efConstruction": 256},
                index_name="hnsw_embedding",
            )

        # Create the collection for each version
        print(f"Creating collections for {VERSION_SELECTION}")
        for version in VERSION_SELECTION:
            self.client.create_collection(collection_name=version, schema=schema)
            self.client.create_index(collection_name=version, index_params=index_params, sync=True)
        print(self.client.list_collections())

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
                            if self.database_type == "dense" or self.database_type == "hybrid":
                                data.append({"dense_embedding": verse_embedding, 
                                            "text": verse_text, 
                                            "version": version, 
                                            "book": book, 
                                            "chapter": chapter, 
                                            "verse": verse_number})
                            elif self.database_type == "sparse":
                                data.append({"text": verse_text, 
                                            "version": version, 
                                            "book": book, 
                                            "chapter": chapter, 
                                            "verse": verse_number})
                        self.client.insert(collection_name=version, data=data)
                        print(f"Added {book} {chapter} to {version} collection")

    def search(self, collection_name: str, query: str, limit: int = 10):
        if self.database_type == "dense" or self.database_type == "hybrid":
            # Get query embedding (single vector)
            query_embedding = EMBEDDING_ENGINE.embed([query], prompt_type="query", normalize=False)[0]
        else:
            query_embedding = None

        # Set up the request types for the hybrid search
        request_types = []

        # Set up the sparse search request
        if self.database_type == "sparse" or self.database_type == "hybrid":
            # Set up BM25 search request on sparse field generated by BM25 function
            sparse_search_params = {"metric_type": "BM25", "params": {"drop_ratio_search": 0.2}}
            sparse_request = AnnSearchRequest([query], "sparse_embedding", sparse_search_params, limit=limit)
            request_types.append(sparse_request)

        # Set up the dense search request
        if self.database_type == "dense" or self.database_type == "hybrid":
            # Set up dense vector search request on your dense field
            dense_search_params = {"metric_type": "COSINE", "params": {"ef": 128}}
            dense_request = AnnSearchRequest([query_embedding], "dense_embedding", dense_search_params, limit=limit)
            request_types.append(dense_request)

        # Perform the sparse search
        if self.database_type == "sparse":
            # BM25 sparse vectors
            sparse_results = self.client.search(
                collection_name=collection_name,
                data=[query],
                anns_field="sparse_embedding",
                limit=limit,
                search_params=sparse_search_params,
                output_fields=["version", "book", "chapter", "verse", "text"],
            )
            return sparse_results[0]

        # Perform the dense search
        if self.database_type == "dense":
            # Dense vectors
            dense_results = self.client.search(
                collection_name=collection_name,
                data=[query_embedding],
                anns_field="dense_embedding",
                limit=limit,
                search_params=dense_search_params,
                output_fields=["version", "book", "chapter", "verse", "text"],
            )
            return dense_results[0]

        # Perform the hybrid search
        if self.database_type == "hybrid":
            sparse_weight = float(os.getenv("SPARSE_WEIGHT", 0.2))
            dense_weight = float(os.getenv("DENSE_WEIGHT", 0.8))

            # Perform hybrid search with reciprocal rank fusion
            hybrid_results = self.client.hybrid_search(
                collection_name=collection_name,
                reqs=request_types,
                ranker=WeightedRanker(sparse_weight, dense_weight),  # Reciprocal Rank Fusion for combining results
                limit=limit,
                output_fields=["version", "book", "chapter", "verse", "text"]
            )
            return hybrid_results[0]

    def get_collection_names(self):
        return self.client.list_collections()

    def close(self):
        self.client.close()