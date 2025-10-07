import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import torch
import gc
import asyncio

# Ensure project root is on sys.path when running this script directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.vdb.embedding import Embedding
load_dotenv()

model_id = os.getenv("EMBEDDING_MODEL_ID", "")
print(f"Model ID: {model_id}")

batch = ["Hello, world!", "hi there"]

async def test_unified_runner_async():
    embedding = Embedding(model_id)
    print(list(await embedding.async_embed(batch)))

if __name__ == "__main__":
    asyncio.run(test_unified_runner_async())