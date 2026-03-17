import inspect
import json
import logging
import os

from pymilvus import MilvusClient, AsyncMilvusClient, CollectionSchema, FieldSchema, DataType, Function, FunctionType, AnnSearchRequest, WeightedRanker

from ai.vdb.embedding import Embedding
import fAIth.bible_globals as bible_globals

# Set up logging
logger = logging.getLogger(__name__)


class VectorDatabaseBuilder:
    """
    Synchronous client for building and managing Milvus vector database collections.

    This class handles database and collection creation, schema definition, and data insertion.
    It supports three embedding strategies: sparse (BM25), dense (HNSW), or hybrid (both).

    Configuration is read from environment variables:
        - MILVUS_HOST, MILVUS_PORT: Connection details
        - MILVUS_DATABASE_NAME: Database name
        - MILVUS_USERNAME, MILVUS_PASSWORD: Authentication credentials
        - DATABASE_TYPE: "sparse", "dense", or "hybrid"
    """

    def __init__(self):
        """
        Initialize the Milvus database builder.

        Loads connection configuration from environment variables and validates the database type.
        Does not establish a database connection yet; call load_or_create_database() after init.

        Raises:
            ValueError: If DATABASE_TYPE is not one of: sparse, dense, hybrid
        """
        # Load Milvus connection configuration
        # Use pre-computed Milvus URL from docker-compose or environment
        milvus_host = str(os.getenv("MILVUS_HOST") or "http://milvus").strip()
        milvus_port = str(os.getenv("MILVUS_PORT") or "19530").strip()

        # Validate Milvus host and port
        if not milvus_host or not milvus_port:
            logger.error("Milvus host or port is not set")
            raise ValueError("Milvus host or port is not set")

        # If Milvus host is not a valid URL, add http:// prefix to make it a valid URL
        if not milvus_host.startswith(("http://", "https://")):
            milvus_host = f"http://{milvus_host}"

        self.milvus_url = f"{milvus_host}:{milvus_port}"
        self.milvus_database_name = str(os.getenv("MILVUS_DATABASE_NAME") or "fAIth").strip()
        self.milvus_username = str(os.getenv("MILVUS_USERNAME") or "root").strip()
        self.milvus_password = os.getenv("MILVUS_PASSWORD")
        if not self.milvus_password or self.milvus_password == "CHANGE_ME_use_a_strong_password":
            raise ValueError("MILVUS_PASSWORD environment variable is not set or was set to the default value")

        # Initialize embedding engine for generating vector embeddings
        self.embedding_engine = Embedding()
        
        # Validate and load database type (determines schema and indexing strategy)
        self.database_type = str(os.getenv("DATABASE_TYPE") or "hybrid").strip().lower()
        if self.database_type not in ["sparse", "dense", "hybrid"]:
            logger.error(f"Invalid database type: {self.database_type}")
            raise ValueError(f"Invalid database type: {self.database_type}. Valid database types are: sparse, dense, hybrid")

        # Establish synchronous connection to Milvus
        self.client = MilvusClient(uri=self.milvus_url, token=f"{self.milvus_username}:{self.milvus_password}")

    def load_database(self):
        """
        Switch to an existing database by name.

        Raises:
            Exception: If the database cannot be loaded.
        """
        # Select the target database for subsequent operations
        try:
            self.client.use_database(self.milvus_database_name)
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            raise e

    def load_or_create_database(self):
        """
        Ensure the database exists, creating it if necessary.

        If the database doesn't exist, creates it and loads it.
        If it exists, loads it immediately.

        Raises:
            Exception: If creation or loading fails.
        """
        # Check if database exists in Milvus
        if self.milvus_database_name not in self.client.list_databases():
            # Create and switch to new database
            try:
                logger.info(f"Database {self.milvus_database_name} does not exist. Creating database.")
                self.client.create_database(self.milvus_database_name)
                self.client.use_database(self.milvus_database_name)
                logger.info(f"Database {self.milvus_database_name} successfully created.")
            except Exception as e:
                logger.error(f"Error creating database: {e}")
                raise e
        else:
            # Database already exists, just switch to it
            try:
                logger.info(f"Database {self.milvus_database_name} exists. Using database.")
                self.load_database()
                logger.info(f"Database {self.milvus_database_name} successfully loaded.")
            except Exception as e:
                logger.error(f"Error loading database: {e}")
                raise e

    def list_collections_in_database(self):
        """
        List all collections in the current database.

        Returns:
            list: Collection names.

        Raises:
            Exception: If the query fails.
        """
        try:
            return self.client.list_collections(db_name=self.milvus_database_name)
        except Exception as e:
            logger.error(f"Error listing collections in database: {e}")
            raise e

    def drop_collection(self, collection_name: str):
        """
        Drop a collection if it exists (non-fatal if it doesn't exist).

        Parameters:
            collection_name (str): Name of the collection to drop.
        """
        try:
            self.client.drop_collection(collection_name=collection_name)
        except Exception as e:
            logger.warning(f"Error dropping collection or collection does not exist: {e}")

    def create_collections(self, collection_names: list[str] | None = None):
        """
        Create collections with appropriate schema and build indices for all Bible verses.

        If no collection_names provided, creates collections for all enabled Bible versions.
        For each collection, drops any existing version, creates schema/indices, then loads verse data.

        Parameters:
            collection_names (list): Specific collection names to create. If empty, uses VERSION_SELECTION.

        Raises:
            ValueError: If any collection name is not in VERSION_SELECTION.

        Workflow:
            1. Determine which collections to create (all versions or specific ones)
            2. Create schema based on database_type (sparse/dense/hybrid)
            3. Configure indices (BM25 for sparse, HNSW for dense)
            4. Load verse data from Bible JSON files
            5. Generate embeddings and insert into collections
        """
        # Determine which collections to create
        collections_to_create = []

        # Option 1: Create all collections from VERSION_SELECTION
        if not collection_names:
            logger.info(f"Creating collections: {bible_globals.VERSION_SELECTION}")
            for collection_name in bible_globals.VERSION_SELECTION:
                self.drop_collection(collection_name)
                collections_to_create.append(collection_name)
        # Option 2: Create only specified collections
        else:
            logger.info(f"Checking validity of collections: {collection_names}")
            # Validate all collection names exist in version selection
            for collection_name in collection_names:
                if collection_name not in bible_globals.VERSION_SELECTION:
                    logger.error(f"Collection {collection_name} does not exist. Skipping.")
                    raise ValueError(f"Collection {collection_name} does not exist.")
            logger.info(f"All collections are valid. Creating collections: {collection_names}")
            for collection_name in collection_names:
                self.drop_collection(collection_name)
                collections_to_create.append(collection_name)

        # Define collection schema based on database type
        logger.info(f"Creating schema for {self.milvus_database_name}")

        if self.database_type == "sparse":
            # Sparse-only schema (BM25 keyword search)
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
        elif self.database_type == "dense":
            # Dense-only schema (semantic similarity search)
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
        elif self.database_type == "hybrid":
            # Hybrid schema (both keyword and semantic search)
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

        # Configure indices for the schema
        index_params = self.client.prepare_index_params()

        # Add sparse (BM25) index if using sparse or hybrid mode
        if self.database_type == "sparse" or self.database_type == "hybrid":
            # BM25 function generates sparse embeddings from text field
            bm25_function = Function(
                name="text_bm25_emb",
                input_field_names=["text"],
                output_field_names=["sparse_embedding"],
                function_type=FunctionType.BM25,
            )
            schema.add_function(bm25_function)
            # Configure sparse inverted index with BM25 scoring
            index_params.add_index(
                field_name="sparse_embedding",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="BM25",
                params={
                    "inverted_index_algo": "DAAT_MAXSCORE",
                    "bm25_k1": 1.2,
                    "bm25_b": 0.75
                }
            )
        
        # Add dense (HNSW) index if using dense or hybrid mode
        if self.database_type == "dense" or self.database_type == "hybrid":
            # HNSW index for fast approximate nearest neighbor search
            index_params.add_index(
                field_name="dense_embedding",
                index_type="HNSW",
                metric_type="COSINE",
                params={"M": 32, "efConstruction": 256},
                index_name="hnsw_embedding",
            )

        # Create collections and indices
        logger.info(f"Creating collections for {collections_to_create}")
        for collection_name in collections_to_create:
            self.client.create_collection(collection_name=collection_name, schema=schema)
            self.client.create_index(collection_name=collection_name, index_params=index_params, sync=True)
        logger.info(f"Collections created: {collections_to_create}")

        # Populate collections with Bible verse data
        logger.info("Populating collections with verse data")
        for collection_name in collections_to_create:
            # Iterate through all books and chapters
            for book in bible_globals.IN_ORDER_BOOKS:
                for chapter in range(1, bible_globals.CHAPTER_SELECTION[book] + 1):
                    # Load chapter JSON file
                    path = bible_globals.BIBLE_DATA_ROOT.joinpath(collection_name, book, f"{chapter}.json")
                    if not path.exists():
                        logger.error(f"Bible data file not found: {path}")
                        continue
                    
                    with path.open("r", encoding="utf-8") as file:
                        verse_numbers = []
                        verse_texts = []
                        json_data = json.load(file)
                        
                        # Extract verse data, skipping headers
                        for verse in json_data.keys():
                            if "header_" in verse:
                                continue
                            verse_numbers.append(int(verse))
                            verse_clean_text = json_data[verse]
                            # Remove HTML tags for cleaner storage (e.g., <span class="wj">...</span>)
                            verse_clean_text = verse_clean_text.replace("<span class=\"wj\">", "").replace("</span>", "").strip()
                            verse_texts.append(verse_clean_text)
                        
                        # Generate embeddings for all verses
                        verse_embeddings = self.embedding_engine.embed(verse_texts, prompt_type="document", normalize=False)

                        # Build data records with embeddings
                        data = []
                        for verse_number, verse_text, verse_embedding in zip(verse_numbers, verse_texts, verse_embeddings):
                            record = {
                                "text": verse_text,
                                "version": collection_name,
                                "book": book,
                                "chapter": chapter,
                                "verse": verse_number
                            }
                            # Include appropriate embedding(s) based on database type
                            if self.database_type == "dense" or self.database_type == "hybrid":
                                record["dense_embedding"] = verse_embedding
                            data.append(record)
                        
                        # Insert records into collection
                        self.client.insert(collection_name=collection_name, data=data)
                        logger.info(f"Added {book} {chapter} to {collection_name} collection")

    def close(self):
        """
        Close the Milvus database connection.

        Raises:
            Exception: If the connection cannot be closed.
        """
        try:
            self.client.close()
        except Exception as e:
            logger.error(f"Error closing database: {e}")
            raise e


class VectorDatabaseQuerier:
    """
    Asynchronous client for querying Milvus vector database.

    Handles search operations across sparse (BM25), dense (semantic), or hybrid search strategies.
    Designed to be used with Django's lifespan manager for app-wide resource management.

    Configuration is read from environment variables:
        - MILVUS_HOST, MILVUS_PORT: Connection details
        - MILVUS_DATABASE_NAME: Database name
        - MILVUS_USERNAME, MILVUS_PASSWORD: Authentication credentials
        - DATABASE_TYPE: "sparse", "dense", or "hybrid"
        - SPARSE_WEIGHT, DENSE_WEIGHT: Weights for hybrid search combination (0.2/0.8 default)
    """

    def __init__(self):
        """
        Initialize the async database querier.

        Loads configuration but does not establish a connection.
        Use load_database_and_collections() class method to create an initialized instance.

        Raises:
            ValueError: If DATABASE_TYPE is not one of: sparse, dense, hybrid
        """
        # Load Milvus connection configuration
        milvus_host = str(os.getenv("MILVUS_HOST") or "http://milvus").strip()
        milvus_port = str(os.getenv("MILVUS_PORT") or "19530").strip()

        if not milvus_host.startswith(("http://", "https://")):
            milvus_host = f"http://{milvus_host}"

        self.milvus_url = f"{milvus_host}:{milvus_port}"
        self.milvus_database_name = str(os.getenv("MILVUS_DATABASE_NAME") or "fAIth").strip()
        self.milvus_username = str(os.getenv("MILVUS_USERNAME") or "root").strip()
        self.milvus_password = os.getenv("MILVUS_PASSWORD")
        if not self.milvus_password or self.milvus_password == "CHANGE_ME_use_a_strong_password":
            raise ValueError("MILVUS_PASSWORD environment variable is not set or was set to the default value")
        self.sparse_weight = float(str(os.getenv("SPARSE_WEIGHT") or 0.2).strip())
        self.dense_weight = float(str(os.getenv("DENSE_WEIGHT") or 0.8).strip())

        # Initialize embedding engine for query embeddings
        self.embedding_engine = Embedding()

        # Validate and load database type (determines search strategy)
        self.database_type = str(os.getenv("DATABASE_TYPE") or "hybrid").strip().lower()
        if self.database_type not in ["sparse", "dense", "hybrid"]:
            logger.error(f"Invalid database type: {self.database_type}")
            raise ValueError(f"Invalid database type: {self.database_type}. Valid database types are: sparse, dense, hybrid")

        # Async client is initialized by load_database_and_collections()
        self.async_client = None

    @classmethod
    async def load_database_and_collections(cls):
        """
        Async factory method to create and initialize a database querier.

        Creates an instance, verifies the database exists, and loads all collections.
        This should be called during application startup via lifespan manager.

        Returns:
            VectorDatabaseQuerier: Initialized and ready-to-query instance.

        Raises:
            ValueError: If the database doesn't exist.
        """
        self = cls()

        # Create temporary client to check database existence
        temp_client = AsyncMilvusClient(
            uri=self.milvus_url,
            token=f"{self.milvus_username}:{self.milvus_password}",
        )
        # List available databases
        databases = await temp_client.list_databases()
        logger.info(f"Databases: {databases}")

        # Verify target database exists
        if self.milvus_database_name not in databases:
            raise ValueError(f"Database {self.milvus_database_name} does not exist")
        else:
            # Create async client with correct database context
            logger.info(f"Using database {self.milvus_database_name}")
            self.async_client = AsyncMilvusClient(
                uri=self.milvus_url,
                token=f"{self.milvus_username}:{self.milvus_password}",
                db_name=self.milvus_database_name,
            )

        # Load all collections into memory for faster queries
        collections = await self.async_client.list_collections()
        logger.info(f"Collections: {collections}")

        for collection in collections:
            await self.async_client.load_collection(collection_name=collection)
            logger.info(f"Loaded collection: {collection}")

        return self
    
    async def list_collections_in_database(self):
        """
        List all collections in the database.

        Returns:
            list: Collection names.

        Raises:
            Exception: If the query fails.
        """
        try:
            return await self.async_client.list_collections()
        except Exception as e:
            logger.error(f"Error listing collections in database: {e}")
            raise e

    async def search(self, collection_name: str, query: str, limit: int = 10):
        """
        Search for verses asynchronously using the configured search strategy.

        For sparse: Uses BM25 keyword matching on text field.
        For dense: Uses HNSW index for semantic similarity search.
        For hybrid: Combines both with weighted rank fusion (BM25 and HNSW).

        Parameters:
            collection_name (str): Name of the Bible version collection to search.
            query (str): User's search query (text or natural language).
            limit (int): Maximum number of results to return (default: 10).

        Returns:
            list: Search results with entity metadata (text, book, chapter, verse, version).

        Raises:
            Exception: If the search fails.
        """
        # Generate query embedding for dense/hybrid search
        if self.database_type == "dense" or self.database_type == "hybrid":
            # Async embedding generation
            query_embedding = (await self.embedding_engine.async_embed([query], prompt_type="query", normalize=False))[0]
        else:
            query_embedding = None

        # Build search request list for hybrid search
        request_types = []

        # Configure sparse (BM25) search if applicable
        if self.database_type == "sparse" or self.database_type == "hybrid":
            sparse_search_params = {"metric_type": "BM25", "params": {"drop_ratio_search": 0.2}}
            sparse_request = AnnSearchRequest([query], "sparse_embedding", sparse_search_params, limit=limit)
            request_types.append(sparse_request)

        # Configure dense (HNSW) search if applicable
        if self.database_type == "dense" or self.database_type == "hybrid":
            dense_search_params = {"metric_type": "COSINE", "params": {"ef": 128}}
            dense_request = AnnSearchRequest([query_embedding], "dense_embedding", dense_search_params, limit=limit)
            request_types.append(dense_request)

        # Perform sparse-only search (BM25 keyword matching)
        if self.database_type == "sparse":
            sparse_results = await self.async_client.search(
                collection_name=collection_name,
                data=[query],
                anns_field="sparse_embedding",
                limit=limit,
                search_params=sparse_search_params,
                output_fields=["version", "book", "chapter", "verse", "text"],
            )
            return sparse_results[0]

        # Perform dense-only search (semantic similarity)
        if self.database_type == "dense":
            dense_results = await self.async_client.search(
                collection_name=collection_name,
                data=[query_embedding],
                anns_field="dense_embedding",
                limit=limit,
                search_params=dense_search_params,
                output_fields=["version", "book", "chapter", "verse", "text"],
            )
            return dense_results[0]

        # Perform hybrid search (combining sparse and dense with weighted rank fusion)
        if self.database_type == "hybrid":
            # Hybrid search combines BM25 and semantic similarity via reciprocal rank fusion
            hybrid_results = await self.async_client.hybrid_search(
                collection_name=collection_name,
                reqs=request_types,
                ranker=WeightedRanker(self.sparse_weight, self.dense_weight),
                limit=limit,
                output_fields=["version", "book", "chapter", "verse", "text"]
            )
            return hybrid_results[0]

    async def close(self):
        """
        Close the async database connection.

        Safely handles both awaitable and non-awaitable close operations.
        """
        if self.async_client is None:
            return
        close_result = self.async_client.close()
        # Check if close() returns an awaitable (async operation)
        if inspect.isawaitable(close_result):
            await close_result
