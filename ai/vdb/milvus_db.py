from pathlib import Path
import sys
import os
import asyncio
import inspect
from pymilvus import MilvusClient, AsyncMilvusClient, CollectionSchema, FieldSchema, DataType, Function, FunctionType, AnnSearchRequest, WeightedRanker
from dotenv import load_dotenv
import json
from frontend.globals import BIBLE_DATA_ROOT, VERSION_SELECTION, IN_ORDER_BOOKS, CHAPTER_SELECTION
from ai.vdb.embedding import Embedding
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class VectorDatabase:
    """Milvus standalone client."""
    def __init__(self):
        """Initialize the Milvus standalone client. Build the database if it doesn't exist."""

        # Get Milvus connection information
        self.milvus_url = os.getenv("MILVUS_URL")
        self.milvus_port = os.getenv("MILVUS_PORT")
        self.milvus_database_name = os.getenv("MILVUS_DATABASE_NAME")
        self.milvus_username = os.getenv("MILVUS_USERNAME")
        self.milvus_password = os.getenv("MILVUS_PASSWORD")

        # Get the embedding engine
        self.embedding_engine = Embedding()
        
        # Get the database type
        self.database_type = os.getenv("DATABASE_TYPE", "hybrid")
        
        # Establish a connection to the Milvus database
        self.client = MilvusClient(uri=f"{self.milvus_url}{':' if self.milvus_port else ''}{self.milvus_port}", token=f"{self.milvus_username}:{self.milvus_password}")

    def load_database(self):
        """Load the database."""
        # Use the database if it exists
        try:
            self.client.use_database(self.milvus_database_name)
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            raise e

    def load_or_create_database(self):
        """Get or create the database."""
        # Check if the database exists
        if self.milvus_database_name not in self.client.list_databases():
            # Create the database
            try:
                logger.info(f"Database {self.milvus_database_name} does not exist. Creating database.")
                self.client.create_database(self.milvus_database_name)
                self.client.use_database(self.milvus_database_name)
                logger.info(f"Database {self.milvus_database_name} successfully created.")
            except Exception as e:
                logger.error(f"Error creating database: {e}")
                raise e
        else:
            # Use the database if it exists
            try:
                logger.info(f"Database {self.milvus_database_name} exists. Using database.")
                self.load_database()
                logger.info(f"Database {self.milvus_database_name} successfully loaded.")
            except Exception as e:
                logger.error(f"Error loading database: {e}")
                raise e

    def list_collections_in_database(self):
        """List the collections in the database."""
        try:
            return self.client.list_collections(db_name=self.milvus_database_name)
        except Exception as e:
            logger.error(f"Error listing collections in database: {e}")
            raise e

    def load_collections_in_database(self):
        """Load the collections in the database."""
        try:
            for collection in self.list_collections_in_database():
                self.client.load_collection(collection_name=collection)
        except Exception as e:
            logger.error(f"Error loading collections in database: {e}")
            raise e

    def drop_collection(self, collection_name: str):
        """Drop the collection."""
        try:
            self.client.drop_collection(collection_name=collection_name)
        except Exception as e:
            logger.warning(f"Error dropping collection or collection does not exist: {e}")

    def create_collections(self, collection_names: list[str] = []):
        """Create the collections."""
        # Rebuild the database
        collections_to_create = []

        # Create all collections in VERSION_SELECTION
        if not collection_names:
            logger.info(f"Creating collections: {VERSION_SELECTION}")
            for collection_name in VERSION_SELECTION:
                self.drop_collection(collection_name)
                collections_to_create.append(collection_name)
        # Create specific collections
        else:
            logger.info(f"Checking validity of collections: {collection_names}")
            for collection_name in collection_names:
                if collection_name not in VERSION_SELECTION:
                    logger.error(f"Collection {collection_name} does not exist. Skipping.")
                    raise ValueError(f"Collection {collection_name} does not exist.")
            logger.info(f"All collections are valid. Creating collections: {collection_names}")
            for collection_name in collection_names:
                self.drop_collection(collection_name)
                collections_to_create.append(collection_name)

        # Create a schema for the collection
        logger.info(f"Creating schema for {self.milvus_database_name}")

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
                    FieldSchema(name="dense_embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_engine.embedding_size()),
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
                    FieldSchema(name="dense_embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_engine.embedding_size()),
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
        index_params = self.client.prepare_index_params()

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
        logger.info(f"Creating collections for {collections_to_create}")
        for collection_name in collections_to_create:
            self.client.create_collection(collection_name=collection_name, schema=schema)
            self.client.create_index(collection_name=collection_name, index_params=index_params, sync=True)
        logger.info(f"Collections created: {collections_to_create}")

        # Add things to the collections
        # Get the Bible version
        for collection_name in collections_to_create:
            # Get the books in order
            for book in IN_ORDER_BOOKS:
                for chapter in range(1, CHAPTER_SELECTION[book] + 1):
                    # Get the verses for the book and chapter
                    path = os.path.join(BIBLE_DATA_ROOT, collection_name, book, f"{chapter}.json")
                    if not os.path.exists(path):
                        logger.error(f"Bible data file not found: {path}")
                        continue
                    with open(path, "r", encoding="utf-8") as file:
                        verse_numbers = []
                        verse_texts = []
                        # Load the JSON data
                        json_data = json.load(file)
                        # Add the verses to the collection
                        for verse in json_data.keys():
                            if "header_" in verse:
                                continue
                            verse_numbers.append(int(verse))
                            verse_clean_text = json_data[verse]
                            # Remove the HTML tags to have cleaner database entries
                            verse_clean_text = verse_clean_text.replace("<span class=\"wj\">", "").replace("</span>", "").strip()
                            verse_texts.append(verse_clean_text)
                        verse_embeddings = self.embedding_engine.embed(verse_texts, prompt_type="document", normalize=False)

                        data = []
                        for verse_number, verse_text, verse_embedding in zip(verse_numbers, verse_texts, verse_embeddings):
                            if self.database_type == "dense" or self.database_type == "hybrid":
                                data.append({"dense_embedding": verse_embedding, 
                                            "text": verse_text, 
                                            "version": collection_name, 
                                            "book": book, 
                                            "chapter": chapter, 
                                            "verse": verse_number})
                            elif self.database_type == "sparse":
                                data.append({"text": verse_text, 
                                            "version": collection_name, 
                                            "book": book, 
                                            "chapter": chapter, 
                                            "verse": verse_number})
                        self.client.insert(collection_name=collection_name, data=data)
                        logger.info(f"Added {book} {chapter} to {collection_name} collection")

    def count_entities_in_collection(self, collection_name: str):
        """Count the entities in the collection."""
        try:
            return self.client.count(collection_name=collection_name, db_name=self.milvus_database_name)
        except Exception as e:
            logger.error(f"Error counting entities in collection: {e}")
            raise e

    def search(self, collection_name: str, query: str, limit: int = 10):
        """Search the database."""
        if self.database_type == "dense" or self.database_type == "hybrid":
            # Get query embedding (single vector)
            query_embedding = self.embedding_engine.embed([query], prompt_type="query", normalize=False)[0]
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

    def close(self):
        """Close the database."""
        try:
            self.client.close()
        except Exception as e:
            logger.error(f"Error closing database: {e}")
            raise e

class AsyncVectorDatabase:
    """Async Milvus standalone client."""
    def __init__(self):
        """Initialize the Async Milvus standalone client."""

        # Get Milvus connection information
        self.milvus_url = os.getenv("MILVUS_URL")
        self.milvus_port = os.getenv("MILVUS_PORT")
        self.milvus_database_name = os.getenv("MILVUS_DATABASE_NAME")
        self.milvus_username = os.getenv("MILVUS_USERNAME")
        self.milvus_password = os.getenv("MILVUS_PASSWORD")

        # Get the embedding engine
        self.embedding_engine = Embedding()

        # Get the database type
        self.database_type = os.getenv("DATABASE_TYPE", "hybrid")

        # Establish a connection to the Milvus database with the correct DB context
        self.async_client = None

    @classmethod
    async def load_database_and_collections(cls):
        """Async factory to instantiate and initialize the database client and load the collections."""
        self = cls()

        # Make a dummy client to check if the database exists
        temp_client = AsyncMilvusClient(
            uri=f"{self.milvus_url}{':' if self.milvus_port else ''}{self.milvus_port}",
            token=f"{self.milvus_username}:{self.milvus_password}",
        )
        # List the databases
        databases = await temp_client.list_databases()
        logger.info(f"Databases: {databases}")

        # Check if the database exists
        if self.milvus_database_name not in databases:
            raise ValueError(f"Database {self.milvus_database_name} does not exist")
        else:
            # Use the database if it exists and load the collections
            logger.info(f"Using database {self.milvus_database_name}")
            self.async_client = AsyncMilvusClient(
                uri=f"{self.milvus_url}{':' if self.milvus_port else ''}{self.milvus_port}",
                token=f"{self.milvus_username}:{self.milvus_password}",
                db_name=self.milvus_database_name,
            )

        # Get the collections
        collections = await self.async_client.list_collections()
        logger.info(f"Collections: {collections}")

        # Load the collections
        for collection in collections:
            await self.async_client.load_collection(collection_name=collection)
            logger.info(f"Loaded collection: {collection}")

        return self
    
    async def list_collections_in_database(self):
        """List the collections in the database."""
        try:
            return await self.async_client.list_collections()
        except Exception as e:
            logger.error(f"Error listing collections in database: {e}")
            raise e

    async def search(self, collection_name: str, query: str, limit: int = 10):
        if self.database_type == "dense" or self.database_type == "hybrid":
            # Get query embedding (single vector) asynchronously
            query_embedding = (await self.embedding_engine.async_embed([query], prompt_type="query", normalize=False))[0]
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
            sparse_results = await self.async_client.search(
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
            dense_results = await self.async_client.search(
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
            hybrid_results = await self.async_client.hybrid_search(
                collection_name=collection_name,
                reqs=request_types,
                ranker=WeightedRanker(sparse_weight, dense_weight),  # Reciprocal Rank Fusion for combining results
                limit=limit,
                output_fields=["version", "book", "chapter", "verse", "text"]
            )
            return hybrid_results[0]

    async def close(self):
        if self.async_client is None:
            return
        close_result = self.async_client.close()
        if inspect.isawaitable(close_result):
            await close_result
