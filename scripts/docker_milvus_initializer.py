import os
import sys
from pathlib import Path
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

# Start Django
try:
    import django
    django.setup()
except Exception as e:
    # Allow script to proceed; some paths may not require Django
    logger.warning(f"Warning: Django setup failed: {e}")

# Get the version selection
from frontend.globals import VERSION_SELECTION
# Import the Milvus database class
from ai.vdb.milvus_db import VectorDatabaseBuilder

# Get DB object
try:
    logger.info("Getting Milvus database builder object")
    vector_database_builder = VectorDatabaseBuilder()
    logger.info("Milvus database builder object obtained")
except Exception as e:
    logger.error(f"Error getting Milvus database builder object: {e}")
    raise e

# See if the database exists
try:
    logger.info("Loading or creating database")
    vector_database_builder.load_or_create_database()
    logger.info("Database loaded or created")
except Exception as e:
    logger.error(f"Error loading or creating database: {e}")
    raise e

# See if the collections exist
try:
    logger.info("Checking if collections exist")
    existing_collections = vector_database_builder.list_collections_in_database()
    logger.info(f"Existing collections: {existing_collections}")
    collections_to_create = []
    # Get the collections that do not exist
    for collection_name in VERSION_SELECTION:
        if collection_name not in existing_collections:
            collections_to_create.append(collection_name)
    # Create the collections that do not exist
    if collections_to_create:
        logger.info(f"The following collections do not exist: {collections_to_create}. Creating them.")
        vector_database_builder.create_collections(collections_to_create)
        logger.info("Collections created.")
    # All collections exist
    else:
        logger.info(f"All collections exist: {existing_collections}")
except Exception as e:
    logger.error(f"Error checking if collections exist: {e}")
    raise e

# Close the database
try:
    logger.info("Closing Milvus database")
    vector_database_builder.close()
    logger.info("Milvus database closed")
except Exception as e:
    logger.warning(f"Milvus database was not closed gracefully: {e}")
