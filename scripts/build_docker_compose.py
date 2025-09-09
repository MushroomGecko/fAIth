import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is on sys.path when running this script directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")
EMBEDDING_MODEL_RUNNER = os.getenv("EMBEDDING_MODEL_RUNNER", "llama_cpp")
EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "Qwen/Qwen3-Embedding-0.6B")

# Llama CPP specific things
EMBEDDING_GPU_LAYERS = int(os.getenv("EMBEDDING_GPU_LAYERS", "0"))
if EMBEDDING_GPU_LAYERS == -1:
    EMBEDDING_GPU_LAYERS = 9999

# vLLM specific things
ENFORCE_EAGER = os.getenv("ENFORCE_EAGER", "False")

DOCKER_COMPOSE_TPL = """
services:
{milvus_setup}
{embedding_setup}
networks:
  default:
    name: milvus
""".lstrip('\n')

NVIDIA_SETUP = \
"""
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
""".lstrip('\n')

MILVUS_SETUP = \
"""
  etcd:
    container_name: milvus-etcd
    image: milvusdb/etcd:latest
    environment:
      - ALLOW_NONE_AUTHENTICATION=yes
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
      - ETCD_LOG_LEVEL=warn
      - ETCD_ADVERTISE_CLIENT_URLS=http://etcd:2379
      - ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/etcd:/etcd
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 30s
      timeout: 20s
      retries: 3

  minio:
    container_name: milvus-minio
    image: minio/minio:latest
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
      MINIO_LOG_LEVEL: warn
    ports:
      - "9001:9001"
      - "9000:9000"
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/minio:/minio_data
    command: minio server /minio_data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  standalone:
    container_name: milvus-standalone
    image: milvusdb/milvus:latest
    command: ["milvus", "run", "standalone"]
    security_opt:
    - seccomp:unconfined
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
      LOG_LEVEL: warn
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/milvus:/var/lib/milvus
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      interval: 30s
      start_period: 90s
      timeout: 20s
      retries: 3
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - "etcd"
      - "minio"
""".lstrip('\n')

OLLAMA_SETUP = \
"""
  ollama:
    container_name: ollama
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    environment:
      OLLAMA_KEEP_ALIVE: 24h
      {ollama_force_cpu}
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/ollama:/root/.ollama
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
{nvidia_setup}
""".lstrip('\n')

LLAMA_CPP_SETUP = \
"""
  llama_cpp:
    container_name: llama-cpp
    image: ghcr.io/ggml-org/llama.cpp:server-cuda
    ports:
      - "8080:8080"
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/llama_cpp:/models
    command: ["-hf", "{model_id}", "-ngl", "{embedding_gpu_layers}", "-c", "4096", "--cache-type-k", "q8_0", "--cache-type-v", "q8_0", "--host", "0.0.0.0", "--port", "8080"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 5
{nvidia_setup}
""".lstrip('\n')

VLLM_SETUP = \
"""
  vllm:
    container_name: vllm
    image: vllm/vllm-openai:latest
    ports:
      - "8000:8000"
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/vllm_cache:/root/.cache/huggingface
    command: ["--model", "{model_id}", "--dtype", "auto", "--max-model-len", "4096", "--enforce-eager", "{enforce_eager}"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
{nvidia_setup}
""".lstrip('\n')

def build_docker_compose():
    """Build the docker compose file."""
    milvus_block = MILVUS_SETUP.format()
    embedding_setup = ""
    
    if EMBEDDING_MODEL_RUNNER == "llama_cpp":
        embedding_setup = LLAMA_CPP_SETUP
    elif EMBEDDING_MODEL_RUNNER == "ollama":
        embedding_setup = OLLAMA_SETUP
    elif EMBEDDING_MODEL_RUNNER == "vllm":
        embedding_setup = VLLM_SETUP
    else:
        raise ValueError(f"Invalid embedding model runner: {EMBEDDING_MODEL_RUNNER}")

    if EMBEDDING_DEVICE == "cpu":
        if EMBEDDING_MODEL_RUNNER == "llama_cpp":
            embedding_setup = embedding_setup.format(model_id=EMBEDDING_MODEL_ID, nvidia_setup="", embedding_gpu_layers=0)
        elif EMBEDDING_MODEL_RUNNER == "ollama":
            embedding_setup = embedding_setup.format(model_id=EMBEDDING_MODEL_ID, nvidia_setup="", ollama_force_cpu="OLLAMA_NUM_GPU=0")
        elif EMBEDDING_MODEL_RUNNER == "vllm":
            embedding_setup = embedding_setup.format(model_id=EMBEDDING_MODEL_ID, nvidia_setup="", enforce_eager=ENFORCE_EAGER)
        else:
            embedding_setup = embedding_setup.format(model_id=EMBEDDING_MODEL_ID, nvidia_setup="")
    elif EMBEDDING_DEVICE == "cuda":
        if EMBEDDING_MODEL_RUNNER == "llama_cpp":
            embedding_setup = embedding_setup.format(model_id=EMBEDDING_MODEL_ID, nvidia_setup=NVIDIA_SETUP, embedding_gpu_layers=EMBEDDING_GPU_LAYERS)
        elif EMBEDDING_MODEL_RUNNER == "ollama":
            embedding_setup = embedding_setup.format(model_id=EMBEDDING_MODEL_ID, nvidia_setup=NVIDIA_SETUP, ollama_force_cpu="")
        elif EMBEDDING_MODEL_RUNNER == "vllm":
            embedding_setup = embedding_setup.format(model_id=EMBEDDING_MODEL_ID, nvidia_setup=NVIDIA_SETUP, enforce_eager=ENFORCE_EAGER)
        else:
            embedding_setup = embedding_setup.format(model_id=EMBEDDING_MODEL_ID, nvidia_setup=NVIDIA_SETUP)
    else:
        raise ValueError(f"Invalid embedding device: {EMBEDDING_DEVICE}")

    docker_compose_str = DOCKER_COMPOSE_TPL.format(
        milvus_setup=milvus_block,
        embedding_setup=embedding_setup,
    )
    return docker_compose_str

if __name__ == "__main__":
    with open("docker-compose.yml", "w") as f:
        f.write(build_docker_compose())