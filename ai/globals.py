import logging
from contextlib import asynccontextmanager

from django_asgi_lifespan.types import LifespanManager

from ai.llm.completions import Completions
from ai.vdb.milvus_db import VectorDatabaseQuerier

# Set up logging
logger = logging.getLogger(__name__)


@asynccontextmanager
async def milvus_db_lifespan_manager() -> LifespanManager:
    """
    Manage the lifecycle of the Milvus vector database connection.

    Initializes the vector database on startup and ensures proper cleanup on shutdown.
    This is used with Django's lifespan event system to manage app-wide resources.

    Yields:
        dict: State dictionary with key "milvus_db" containing the VectorDatabaseQuerier instance.

    Raises:
        Exception: Any exception during database initialization will propagate to the caller.
    """
    logger.info("Initializing Async Milvus database lifecycle manager")

    # Initialize and load Milvus database with all collections
    milvus_db = await VectorDatabaseQuerier.load_database_and_collections()
    state = {
        "milvus_db": milvus_db
    }

    try:
        yield state
    finally:
        # Ensure graceful shutdown even if errors occur
        logger.info("Closing Async Milvus database")
        try:
            await milvus_db.close()
        except Exception as e:
            logger.error(f"Error closing Async Milvus database: {e}")
            pass


@asynccontextmanager
async def completions_lifespan_manager() -> LifespanManager:
    """
    Manage the lifecycle of the LLM Completions object.

    Initializes the LLM completions service on startup and ensures proper cleanup on shutdown.
    This is used with Django's lifespan event system to manage app-wide resources.

    Yields:
        dict: State dictionary with key "completions_obj" containing the Completions instance.

    Raises:
        Exception: Any exception during completions initialization will propagate to the caller.
    """
    logger.info("Initializing Completions object lifecycle manager")

    # Initialize the LLM Completions object
    completions_obj = Completions()
    state = {
        "completions_obj": completions_obj
    }

    try:
        yield state
    finally:
        # Ensure graceful shutdown even if errors occur
        logger.info("Closing Completions object")
        try:
            await completions_obj.close()
        except Exception as e:
            logger.error(f"Error closing Completions object: {e}")
            pass
