import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# Ensure project root is on sys.path when running this script directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.vdb.embedding import Embedding
import fAIth.settings
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

batch = ["Hello, world!", "hi there"]

def test_unified_runner():
    embedding = Embedding()
    logger.info(list(embedding.embed(batch)))

if __name__ == "__main__":
    try:
        test_unified_runner()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise e