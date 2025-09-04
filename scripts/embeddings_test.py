import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import torch
import gc

# Ensure project root is on sys.path when running this script directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fAIth.ai.embedding.runners.docker_model_runner import EmbeddingRunner as DockerRunner
from fAIth.ai.embedding.runners.hf_sentence_transformers import EmbeddingRunner as HFRunner
from fAIth.ai.embedding.runners.llama_cpp_python import EmbeddingRunner as LLamaCPPRunner
from fAIth.ai.embedding.runners.ollama import EmbeddingRunner as OllamaRunner

load_dotenv()

batch = ["Hello, world!", "hi there"]

def test_docker_model_runner():
    model_id = "hf.co/qwen/qwen3-embedding-0.6b-gguf:q8_0"
    runner = DockerRunner(model_id)
    vectors = list(runner.embed(batch))
    print(vectors)
    print(len(vectors))
    
    runner.kill()
    del runner
    torch.cuda.empty_cache()
    gc.collect()

def test_hf_sentence_transformers():
    model_id = "Qwen/Qwen3-Embedding-0.6B"
    runner = HFRunner(model_id)
    vectors = list(runner.embed(batch))
    print(vectors)
    print(len(vectors))

    runner.kill()
    del runner
    torch.cuda.empty_cache()
    gc.collect()

def test_llama_cpp_python():
    repo_id = "Qwen/Qwen3-Embedding-0.6B-GGUF"
    model_id = "Qwen3-Embedding-0.6B-Q8_0.gguf"
    runner = LLamaCPPRunner(model_id, repo_id)
    vectors = list(runner.embed(batch))
    print(vectors)
    print(len(vectors))
    
    runner.kill()
    del runner
    torch.cuda.empty_cache()
    gc.collect()

def test_ollama():
    model_id = "snowflake-arctic-embed:22m"
    runner = OllamaRunner(model_id)
    vectors = list(runner.embed(batch))
    print(vectors)
    print(len(vectors))
        
    runner.kill()
    del runner
    torch.cuda.empty_cache()
    gc.collect()

# Use an embedding-capable model served by your Docker OpenAI-compatible server
# test_docker_model_runner()
# test_hf_sentence_transformers()
# test_llama_cpp_python()
# test_ollama()