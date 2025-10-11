import os
import asyncio
from django.utils.functional import SimpleLazyObject
from ai.vdb.milvus_db import AsyncVectorDatabase
import logging

# Set up logging
logger = logging.getLogger(__name__)


async_milvus_db = None
async_milvus_db_loop = None
async_milvus_db_lock = asyncio.Lock()

async def get_milvus_db():
    global async_milvus_db, async_milvus_db_loop
    current_loop = asyncio.get_running_loop()

    # Fast path: same active loop and cached instance
    if async_milvus_db is not None and async_milvus_db_loop is current_loop and not current_loop.is_closed():
        logger.info("Using cached Async Milvus database")
        return async_milvus_db

    async with async_milvus_db_lock:
        # Re-check under lock
        if async_milvus_db is not None and async_milvus_db_loop is current_loop and not current_loop.is_closed():
            logger.info("Using cached Async Milvus database")
            return async_milvus_db
        # If cached for a different/closed loop, close it
        if async_milvus_db is not None and async_milvus_db_loop is not current_loop:
            try:
                await async_milvus_db.close()
            except Exception as e:
                logger.warning(f"Error closing Async Milvus database: {e}")
                pass
            async_milvus_db = None
        
        # Create on the current loop
        logger.info("Creating new Async Milvus database")
        async_milvus_db = await AsyncVectorDatabase.load_database()
        async_milvus_db_loop = current_loop
        
        return async_milvus_db
