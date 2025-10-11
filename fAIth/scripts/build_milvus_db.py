import logging

# Set up logging
logger = logging.getLogger(__name__)

import os
import sys
from pathlib import Path

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

# Import the Milvus database class
from ai.vdb.milvus_db import VectorDatabase

# Get DB object
try:
    logger.info("Getting Milvus database object")
    vector_database = VectorDatabase()
    logger.info("Milvus database object obtained")
except Exception as e:
    logger.error(f"Error getting Milvus database object: {e}")
    raise e

# Print the collection names
try:
    logger.info("Getting collection names")
    logger.info(vector_database.get_collection_names())
    logger.info("Collection names obtained")
except Exception as e:
    logger.error(f"Error getting collection names: {e}")
    raise e

# Build the database
try:
    logger.info("Building Milvus database")
    vector_database.build_database()
    logger.info("Milvus database built")
except Exception as e:
    logger.error(f"Error building Milvus database: {e}")
    raise e

# Print the collection names
try:
    logger.info("Getting collection names")
    logger.info(vector_database.get_collection_names())
    logger.info("Collection names obtained")
except Exception as e:
    logger.error(f"Error getting collection names: {e}")
    raise e

# Close the database
try:
    logger.info("Closing Milvus database")
    vector_database.close()
    logger.info("Milvus database closed")
except Exception as e:
    logger.warning(f"Milvus database was not closed gracefully: {e}")
