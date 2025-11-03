from contextlib import asynccontextmanager
from django_asgi_lifespan.types import LifespanManager
from ai.vdb.milvus_db import AsyncVectorDatabase
from ai.llm.completions import Completions
import logging

# Set up logging
logger = logging.getLogger(__name__)

@asynccontextmanager
async def milvus_db_lifespan_manager() -> LifespanManager:
    """Lifespan manager for the Async Milvus database."""
    logger.info("Initializing Async Milvus database lifecycle manager")

    # Load the Async Milvus database
    milvus_db = await AsyncVectorDatabase.load_database_and_collections()
    state = {
        "milvus_db": milvus_db
    }

    try:
        yield state
    finally:
        # Shut down the Async Milvus database
        logger.info("Closing Async Milvus database")
        try:
            await milvus_db.close()
        except Exception as e:
            logger.error(f"Error closing Async Milvus database: {e}")
            pass

@asynccontextmanager
async def completions_lifespan_manager() -> LifespanManager:
    """Lifespan manager for the Completions object."""
    logger.info("Initializing Completions object lifecycle manager")

    # Load the Completions object
    completions_obj = Completions()
    state = {
        "completions_obj": completions_obj
    }

    try:
        yield state
    finally:
        # Shut down the Completions object
        logger.info("Closing Completions object")
        try:
            await completions_obj.close()
        except Exception as e:
            logger.error(f"Error closing Completions object: {e}")
            pass
