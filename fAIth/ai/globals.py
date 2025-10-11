import os
import asyncio
from django.utils.functional import SimpleLazyObject
from ai.vdb.milvus_db import AsyncVectorDatabase
import logging

# Set up logging
logger = logging.getLogger(__name__)


ASYNC_MILVUS_DB = None
ASYNC_MILVUS_DB_LOOP = None
ASYNC_MILVUS_DB_LOCK = asyncio.Lock()

async def get_milvus_db():
    global ASYNC_MILVUS_DB, ASYNC_MILVUS_DB_LOOP
    current_loop = asyncio.get_running_loop()

    # Fast path: same active loop and cached instance
    if ASYNC_MILVUS_DB is not None and ASYNC_MILVUS_DB_LOOP is current_loop and not current_loop.is_closed():
        logger.info("Using cached Async Milvus database")
        return ASYNC_MILVUS_DB

    async with ASYNC_MILVUS_DB_LOCK:
        # Re-check under lock
        if ASYNC_MILVUS_DB is not None and ASYNC_MILVUS_DB_LOOP is current_loop and not current_loop.is_closed():
            logger.info("Using cached Async Milvus database")
            return ASYNC_MILVUS_DB
        # If cached for a different/closed loop, close it
        if ASYNC_MILVUS_DB is not None and ASYNC_MILVUS_DB_LOOP is not current_loop:
            try:
                await ASYNC_MILVUS_DB.close()
            except Exception as e:
                logger.warning(f"Error closing Async Milvus database: {e}")
                pass
            ASYNC_MILVUS_DB = None
        
        # Create on the current loop
        logger.info("Creating new Async Milvus database")
        ASYNC_MILVUS_DB = await AsyncVectorDatabase.load_database()
        ASYNC_MILVUS_DB_LOOP = current_loop
        
        return ASYNC_MILVUS_DB
