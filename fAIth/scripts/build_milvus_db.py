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

try:
    import django
    django.setup()
except Exception as e:
    # Allow script to proceed; some paths may not require Django
    logger.warning(f"Warning: Django setup failed: {e}")

from ai.vdb.milvus_db import VectorDatabase

# Get DB object
vector_database = VectorDatabase()

# Print the collection names
logger.info(vector_database.get_collection_names())

# Build the database
vector_database.build_database()

# Print the collection names
logger.info(vector_database.get_collection_names())

# Close the database
vector_database.close()
