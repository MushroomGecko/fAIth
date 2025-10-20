import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# Ensure project root is on sys.path when running this script directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.llm.completions import Completions
import fAIth.settings
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

system_prompt = open("ai/llm/prompts/testing/system.txt", "r").read()
user_prompt = open("ai/llm/prompts/testing/user.txt", "r").read()
query = "Name the 12 apostles of Jesus Christ."

def test_unified_runner_sync():
    llm = Completions()
    logger.info(llm.completions(system_prompt, user_prompt, query))

if __name__ == "__main__":
    try:
        test_unified_runner_sync()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise e