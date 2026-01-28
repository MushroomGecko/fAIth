import os
import sys
from pathlib import Path
import asyncio
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Ensure project root is on sys.path when running this script directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configure Django so modules that depend on settings can import
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ["DJANGO_SETTINGS_MODULE"] = "fAIth.settings"

try:
    import django
    django.setup()
except Exception as e:
    # Allow script to proceed; some paths may not require Django
    logger.warning(f"Warning: Django setup failed: {e}")

from ai.vdb.milvus_db import VectorDatabaseQuerier

async def main():
    # Get DB object
    vector_database_querier = await VectorDatabaseQuerier.load_database_and_collections()
    
    # Print the collection names
    logger.info(await vector_database_querier.list_collections_in_database())

    collection_name = "bsb"
    queries = ["In the beginning", "Sodom and Gomorrah", "Garden of Eden", "Tower of Babel", "Adam and Eve", "What was the name of the first man?", "Noah's Arc", "Noah's Ark", "For God so loves the world", "Jesus said"]
    limit = 10
    for query in queries:
        # Get results
        results = await vector_database_querier.search(collection_name=collection_name, query=query, limit=limit)

        # Print results
        logger.info("\n########################")
        logger.info(f"Results for \"{query}\":")

        # Print results
        logger.info(f"{vector_database_querier.database_type} Search:")
        for i, result in enumerate(results):
            logger.info(f"{i+1}. Score: {result['distance']:.4f}, Content: {result['entity']['text']}, Citation: {result['entity']['book']} {result['entity']['chapter']}:{result['entity']['verse']} {result['entity']['version']}")
    # Cleanly close async client to avoid warnings/errors
    await vector_database_querier.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error: {e}")
        raise e