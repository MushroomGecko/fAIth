import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is on sys.path when running this script directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

# Webapp specific things
WEBAPP_PORT = os.getenv("WEBAPP_PORT", 8000)
UVICORN_WORKERS = os.getenv("UVICORN_WORKERS", 1)

# Postgres specific things
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "faith_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres-secure-password")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "faith_db")

# Milvus specific things
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")

# Hugging Face specific things
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Healthcheck specific things
START_PERIOD = "3600s"
INTERVAL = "30s"
TIMEOUT = "30s"
RETRIES = 5

COMPATBILITY_LIST = \
"""
Drivers:
    - `cpu`
        Runners:
            - `ollama`
                Devices:
                    - `cpu`
                    - `nvidia`
                    - `amd`
                    - `intel`
            - `llama_cpp`
                Devices:
                    - `cpu`
                    - `nvidia`
                    - `amd`
                    - `intel`
            - `vllm`
                Devices:
                    - `cpu`
                    - `nvidia`
                    - `amd`
                    - `intel`
            - `sglang`
                Devices:
                    - `cpu`
                    - `nvidia`
                    - `amd`
                    - `intel`
        NOTE: You may want to consider using a GPU driver if you are using a GPU device (`nvidia`, `amd`, `intel`).
    - `cuda`
        Runners:
            - `ollama`
                Devices:
                    - `nvidia`
            - `llama_cpp`
                Devices:
                    - `nvidia`
            - `vllm`
                Devices:
                    - `nvidia`
            - `sglang`
                Devices:
                    - `nvidia`
    - `rocm`
        Runners:
            - `ollama`
                Devices:
                    - `amd`
            - `llama_cpp`
                Devices:
                    - `amd`
            - `vllm`
                Devices:
                    - `amd`
            - `sglang`
                Devices:
                    - `amd`
    - `vulkan`
        Runners:
            - `llama_cpp`
                Devices:
                    - `nvidia`
                    - `amd`
                    - `intel`
""".lstrip('\n')

DOCKER_COMPOSE_TPL = """
services:
{postgres_setup}

{etcd_setup}

{seaweedfs_setup}

{milvus_setup}

{embedding_setup}

{llm_setup}

{webapp_setup}
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

AMD_SETUP = \
"""
    devices:
      - /dev/kfd
      - /dev/dri
    group_add: [video, render]
    security_opt:
      - seccomp=unconfined
""".lstrip('\n')

INTEL_SETUP = \
"""
    devices:
      - /dev/dri
    group_add: [video, render]
""".lstrip('\n')

POSTGRES_SETUP = \
"""
  postgres:
    container_name: postgres-faith
    image: postgres:latest
    ports:
      - "{postgres_port}:5432"
    environment:
      POSTGRES_USER: {postgres_user}
      POSTGRES_PASSWORD: {postgres_password}
      POSTGRES_DB: {postgres_database}
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/postgres:/var/lib/postgresql
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "{postgres_user}", "-d", "{postgres_database}"]
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
""".lstrip('\n')

ETCD_SETUP = \
"""
  etcd:
    container_name: etcd-faith
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
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
""".lstrip('\n')

SEAWEEDFS_SETUP = \
"""
  seaweedfs-master:
    container_name: seaweedfs-master-faith
    image: chrislusf/seaweedfs:4.03
    ports:
      - 9333:9333
      - 19333:19333
      - 9324:9324
    command: 'master -ip=seaweedfs-master -ip.bind=0.0.0.0 -metricsPort=9324 -mdir=/data'
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/seaweedfs/master:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9333/cluster/status"]
      interval: {interval}
      timeout: {timeout}
      retries: {retries}

  seaweedfs-volume:
    container_name: seaweedfs-volume-faith
    image: chrislusf/seaweedfs:4.03
    ports:
      - 8080:8080
      - 18080:18080
      - 9325:9325
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/seaweedfs/volume:/data
    command: 'volume -ip=seaweedfs-volume -master="seaweedfs-master:9333" -ip.bind=0.0.0.0 -port=8080 -metricsPort=9325 -dir=/data'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/status"]
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
    depends_on:
      seaweedfs-master:
        condition: service_healthy

  seaweedfs-filer:
    container_name: seaweedfs-filer-faith
    image: chrislusf/seaweedfs:4.03
    ports:
      - 8888:8888
      - 18888:18888
      - 9326:9326
    command: 'filer -ip=seaweedfs-filer -master="seaweedfs-master:9333" -ip.bind=0.0.0.0 -metricsPort=9326'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8888/"]
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
    tty: true
    stdin_open: true
    depends_on:
      seaweedfs-master:
        condition: service_healthy
      seaweedfs-volume:
        condition: service_healthy

  seaweedfs-s3:
    container_name: seaweedfs-s3-faith
    image: chrislusf/seaweedfs:4.03
    ports:
      - 8333:8333
      - 9327:9327
    environment:
      AWS_ACCESS_KEY_ID: minioadmin
      AWS_SECRET_ACCESS_KEY: minioadmin
    command: 's3 -filer="seaweedfs-filer:8888" -ip.bind=0.0.0.0 -metricsPort=9327'
    healthcheck:
      test: ["CMD", "curl", "http://localhost:8333/"]
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
    depends_on:
      seaweedfs-master:
        condition: service_healthy
      seaweedfs-volume:
        condition: service_healthy
      seaweedfs-filer:
        condition: service_healthy

  seaweedfs-init:
    container_name: seaweedfs-init-faith
    image: amazon/aws-cli:latest
    environment:
      AWS_ACCESS_KEY_ID: minioadmin
      AWS_SECRET_ACCESS_KEY: minioadmin
      AWS_DEFAULT_REGION: us-east-1
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        echo "Waiting for SeaweedFS S3 to be ready..."
        until aws --endpoint-url=http://seaweedfs-s3:8333 s3 ls 2>/dev/null; do
          echo "SeaweedFS S3 not ready yet, waiting..."
          sleep 2
        done
        echo "Checking if milvus-bucket exists..."
        if aws --endpoint-url=http://seaweedfs-s3:8333 s3api head-bucket --bucket milvus-bucket 2>/dev/null; then
          echo "Bucket milvus-bucket already exists"
        else
          echo "Creating milvus-bucket..."
          if aws --endpoint-url=http://seaweedfs-s3:8333 s3 mb s3://milvus-bucket; then
            echo "Bucket milvus-bucket created successfully"
          else
            echo "ERROR: Failed to create bucket milvus-bucket. Try: docker compose down -v && sudo rm -rf ./volumes"
            exit 1
          fi
        fi
        echo "Bucket initialization complete"
    depends_on:
      seaweedfs-s3:
        condition: service_healthy
""".lstrip('\n')

MILVUS_SETUP = \
"""
  milvus:
    container_name: milvus-faith
    image: milvusdb/milvus:latest
    ports:
      - "{milvus_port}:{milvus_port}"
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: seaweedfs-s3:8333
      MINIO_ACCESS_KEY_ID: minioadmin
      MINIO_SECRET_ACCESS_KEY: minioadmin
      MINIO_USE_SSL: "false"
      MINIO_BUCKET_NAME: milvus-bucket
      MINIO_ROOT_PATH: milvus/data
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/milvus:/var/lib/milvus
    command: ["milvus", "run", "standalone"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      start_period: {start_period}
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
    security_opt:
      - seccomp:unconfined
    depends_on:
      etcd:
        condition: service_healthy
      seaweedfs-s3:
        condition: service_healthy
      seaweedfs-init:
        condition: service_completed_successfully
      embedding:
        condition: service_healthy
""".lstrip('\n')

OLLAMA_SETUP = \
"""
  {model_type}:
    container_name: ollama-{model_type}-faith
    image: {ollama_image}
    ports:
      - "{llm_port}:{llm_port}"
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/ollama:/root/.ollama
    environment:
      OLLAMA_HOST: 0.0.0.0:{llm_port}
      OLLAMA_MODELS: /root/.ollama
      OLLAMA_KEEP_ALIVE: 24h
      {ollama_force_cpu}
    command: ["serve"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{llm_port}/api/tags"]
      start_period: {start_period}
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
{gpu_setup}
""".lstrip('\n')

LLAMA_CPP_SETUP = \
"""
  {model_type}:
    container_name: llama-cpp-{model_type}-faith
    image: {llama_cpp_image}
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/llama_cpp_cache:/root/.cache/huggingface
    ports:
      - "{llm_port}:{llm_port}"
    environment:
      HF_TOKEN: {hf_token}
      HF_HOME: /root/.cache/huggingface
      HUGGINGFACE_HUB_CACHE: /root/.cache/huggingface
    command: ["-hf", "{model_id}", "-c", "{max_context_length}", "-ngl", "{llama_cpp_gpu_layers}", "--cache-type-k", "q8_0", "--cache-type-v", "q8_0", "--host", "0.0.0.0", "--port", "{llm_port}", "--cont-batching", "-np", "{llama_cpp_concurrency}", {embedding}]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{llm_port}/health"]
      start_period: {start_period}
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
{gpu_setup}
""".lstrip('\n')

VLLM_SETUP = \
"""
  {model_type}:
    container_name: vllm-{model_type}-faith
    image: {vllm_image}
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/vllm_cache:/root/.cache/huggingface
    ports:
      - "{llm_port}:{llm_port}"
    environment:
      HF_TOKEN: {hf_token}
      HF_HOME: /root/.cache/huggingface
      HUGGINGFACE_HUB_CACHE: /root/.cache/huggingface
    command: ["--model", "{model_id}", "--download-dir", "/root/.cache/huggingface", "--max-model-len", "{max_context_length}", "--dtype", "auto", "--enforce-eager", "{vllm_enforce_eager}", "--host", "0.0.0.0", "--port", "{llm_port}"]
    ipc: host
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{llm_port}/health"]
      start_period: {start_period}
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
{gpu_setup}
""".lstrip('\n')

SGLANG_SETUP = \
"""
  {model_type}:
    container_name: sglang-{model_type}-faith
    image: {sglang_image}
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/sglang_cache:/root/.cache/huggingface
    network_mode: host # required by RDMA
    privileged: true # required by RDMA
    ports:
      - "{llm_port}:{llm_port}"
    environment:
      HF_TOKEN: {hf_token}
      HF_HOME: /root/.cache/huggingface
      HUGGINGFACE_HUB_CACHE: /root/.cache/huggingface
    command: ["python", "-m", "sglang.launch_server", "--model-path", "{model_id}", "--max-total-tokens", "{max_context_length}", "--disable-cuda-graph", "--host", "0.0.0.0", "--port", "{llm_port}"]
    ipc: host
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{llm_port}/health"]
      start_period: {start_period}
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
{gpu_setup}
""".lstrip('\n')

WEBAPP_SETUP = \
"""
  webapp:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: webapp-faith
    ports:
      - "{webapp_port}:{webapp_port}"
    env_file:
      - .env
    environment:
      POSTGRES_HOST: postgres
      MILVUS_URL: http://milvus
      EMBEDDING_URL: http://embedding
      LLM_URL: http://llm
    command: sh -c "python scripts/docker_milvus_initializer.py && python manage.py migrate && python manage.py collectstatic --noinput --clear && uvicorn fAIth.asgi:application --host 0.0.0.0 --port {webapp_port} --workers {uvicorn_workers}"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{webapp_port}/healthcheck/"]
      start_period: {start_period}
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
    depends_on:
      postgres:
        condition: service_healthy
      milvus:
        condition: service_healthy
      embedding:
        condition: service_healthy
      llm:
        condition: service_healthy
    volumes:
      - .:/app
""".lstrip('\n')

SHELL_ENTRYPOINT = \
"""
#!/bin/sh

set -euo

log() {{
    printf '[ENTRYPOINT] %s\n' "$1"
}}

log "Running Milvus initialization"
python scripts/docker_milvus_initializer.py

log "Running database migrations"
python manage.py migrate

log "Collecting static files"
python manage.py collectstatic --noinput --clear

log "Fixing permissions on /app/staticfiles"
if [ -d /app/staticfiles ]; then
    chown -R faith_user:faith_user /app/staticfiles
fi

log "Starting application server as faith_user"
exec su faith_user -c "uvicorn fAIth.asgi:application --host 0.0.0.0 --port {webapp_port} --workers {uvicorn_workers}"
""".lstrip('\n')

def build_docker_compose(llm_port, model_id, embedding, max_context_length, runner, gpu_type, driver, llama_cpp_gpu_layers, llama_cpp_concurrency, vllm_enforce_eager, start_period, interval, timeout, retries):
    """Build the docker compose file."""
    embedding_setup = '"--embedding"' if embedding else ''
    model_type = "embedding" if embedding else "llm"
    
    if runner == "llama_cpp":
        runner_setup = LLAMA_CPP_SETUP
    elif runner == "ollama":
        runner_setup = OLLAMA_SETUP
    elif runner == "vllm":
        runner_setup = VLLM_SETUP
    elif runner == "sglang":
        runner_setup = SGLANG_SETUP
    else:
        raise ValueError(f"Invalid model runner: `{runner}`")

    if gpu_type == "nvidia":
        gpu_setup = NVIDIA_SETUP
    elif gpu_type == "amd":
        gpu_setup = AMD_SETUP
    elif gpu_type == "intel":
        gpu_setup = INTEL_SETUP
    elif gpu_type == "cpu":
        gpu_setup = ""
    else:
        raise ValueError(f"Invalid GPU type: `{gpu_type}`")
    
    if driver == "cpu":
        if gpu_type != "cpu":
            if embedding:
                print(f"WARNING: Using CPU driver with GPU type `{gpu_type}`. If this is not intended, please check your `EMBEDDING_DRIVER` environment variable.")
            else:
                print(f"WARNING: Using CPU driver with GPU type `{gpu_type}`. If this is not intended, please check your `LLM_DRIVER` environment variable.")

        if runner == "ollama":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, gpu_setup="", ollama_force_cpu="OLLAMA_NUM_GPU=0", ollama_image="ollama/ollama:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "llama_cpp":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup="", llama_cpp_gpu_layers=llama_cpp_gpu_layers, llama_cpp_image="ghcr.io/ggml-org/llama.cpp:server", hf_token=HF_TOKEN, embedding=embedding_setup, llama_cpp_concurrency=llama_cpp_concurrency, model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "vllm":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup="", vllm_enforce_eager=vllm_enforce_eager, hf_token=HF_TOKEN, vllm_image="vllm/vllm-openai:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "sglang":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup="", hf_token=HF_TOKEN, sglang_image="lmsysorg/sglang:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        else:
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATBILITY_LIST}")
    
    elif driver == "cuda":
        if gpu_type != "nvidia":
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATBILITY_LIST}")

        if runner == "ollama":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, gpu_setup=NVIDIA_SETUP, ollama_force_cpu="", ollama_image="ollama/ollama:latest", model_type=model_type)
        elif runner == "llama_cpp":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=NVIDIA_SETUP, llama_cpp_gpu_layers=llama_cpp_gpu_layers, llama_cpp_image="ghcr.io/ggml-org/llama.cpp:server-cuda", hf_token=HF_TOKEN, embedding=embedding_setup, llama_cpp_concurrency=llama_cpp_concurrency, model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "vllm":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=NVIDIA_SETUP, vllm_enforce_eager=vllm_enforce_eager, hf_token=HF_TOKEN, vllm_image="vllm/vllm-openai:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "sglang":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=NVIDIA_SETUP, hf_token=HF_TOKEN, sglang_image="lmsysorg/sglang:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        else:
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`")
    
    elif driver == "rocm":
        if gpu_type != "amd":
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATBILITY_LIST}")

        if runner == "ollama":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, gpu_setup=AMD_SETUP, ollama_force_cpu="", ollama_image="ollama/ollama:rocm", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "llama_cpp":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=AMD_SETUP, llama_cpp_gpu_layers=llama_cpp_gpu_layers, llama_cpp_image="ghcr.io/ggml-org/llama.cpp:server-rocm", hf_token=HF_TOKEN, embedding=embedding_setup, llama_cpp_concurrency=llama_cpp_concurrency, model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "vllm":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=AMD_SETUP, vllm_enforce_eager=vllm_enforce_eager, hf_token=HF_TOKEN, vllm_image="rocm/vllm:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "sglang":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=AMD_SETUP, hf_token=HF_TOKEN, sglang_image="lmsysorg/sglang:dsv32-rocm", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        else:
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATBILITY_LIST}")
    
    elif driver == "vulkan":
        if gpu_type == "cpu":
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATBILITY_LIST}")

        if runner == "llama_cpp":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=gpu_setup, llama_cpp_gpu_layers=llama_cpp_gpu_layers, llama_cpp_image="ghcr.io/ggml-org/llama.cpp:server-vulkan", hf_token=HF_TOKEN, embedding=embedding_setup, llama_cpp_concurrency=llama_cpp_concurrency, model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        else:
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATBILITY_LIST}")
    
    else:
        raise ValueError(f"Invalid driver: `{driver}`. Please check the compatibility list:\n{COMPATBILITY_LIST}")

    print(f"Using `{runner}` with GPU type `{gpu_type}` on driver `{driver}`")
    return runner_setup

if __name__ == "__main__":
    # Embedding specific things
    EMBEDDING_PORT = os.getenv("EMBEDDING_PORT", "11435")
    EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "Qwen/Qwen3-Embedding-0.6B")
    EMBEDDING_MAX_CONTEXT_LENGTH = int(os.getenv("EMBEDDING_MAX_CONTEXT_LENGTH", 4096))
    EMBEDDING_MODEL_RUNNER = os.getenv("EMBEDDING_MODEL_RUNNER", "llama_cpp")
    EMBEDDING_GPU_TYPE = os.getenv("EMBEDDING_GPU_TYPE", "cpu")
    EMBEDDING_DRIVER = os.getenv("EMBEDDING_DRIVER", "cpu")
    EMBEDDING_VLLM_ENFORCE_EAGER = os.getenv("EMBEDDING_VLLM_ENFORCE_EAGER", "False")
    EMBEDDING_LLAMA_CPP_GPU_LAYERS = int(os.getenv("EMBEDDING_LLAMA_CPP_GPU_LAYERS", 0))
    if EMBEDDING_LLAMA_CPP_GPU_LAYERS == -1:
        EMBEDDING_LLAMA_CPP_GPU_LAYERS = 9999
    EMBEDDING_VLLM_ENFORCE_EAGER = os.getenv("EMBEDDING_VLLM_ENFORCE_EAGER", "False")
    EMBEDDING_LLAMA_CPP_CONCURRENCY = int(os.getenv("EMBEDDING_LLAMA_CPP_CONCURRENCY", 2))

    # LLM specific things
    LLM_PORT = os.getenv("LLM_PORT", "11436")
    LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M")
    LLM_MAX_CONTEXT_LENGTH = int(os.getenv("LLM_MAX_CONTEXT_LENGTH", 4096))
    LLM_MODEL_RUNNER = os.getenv("LLM_MODEL_RUNNER", "llama_cpp")
    LLM_GPU_TYPE = os.getenv("LLM_GPU_TYPE", "cpu")
    LLM_DRIVER = os.getenv("LLM_DRIVER", "cpu")
    LLM_LLAMA_CPP_GPU_LAYERS = int(os.getenv("LLM_LLAMA_CPP_GPU_LAYERS", 0))
    if LLM_LLAMA_CPP_GPU_LAYERS == -1:
        LLM_LLAMA_CPP_GPU_LAYERS = 9999
    LLM_LLAMA_CPP_CONCURRENCY = int(os.getenv("LLM_LLAMA_CPP_CONCURRENCY", 2))
    LLM_VLLM_ENFORCE_EAGER = os.getenv("LLM_VLLM_ENFORCE_EAGER", "False")

    postgres_block = POSTGRES_SETUP.format(postgres_port=POSTGRES_PORT, postgres_user=POSTGRES_USER, postgres_password=POSTGRES_PASSWORD, postgres_database=POSTGRES_DATABASE, start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)
    etcd_block = ETCD_SETUP.format(start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)
    seaweedfs_block = SEAWEEDFS_SETUP.format(start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)
    milvus_block = MILVUS_SETUP.format(milvus_port=MILVUS_PORT, start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)
    embedding_block = build_docker_compose(llm_port=EMBEDDING_PORT, model_id=EMBEDDING_MODEL_ID, embedding=True, max_context_length=EMBEDDING_MAX_CONTEXT_LENGTH, runner=EMBEDDING_MODEL_RUNNER, gpu_type=EMBEDDING_GPU_TYPE, driver=EMBEDDING_DRIVER, llama_cpp_gpu_layers=EMBEDDING_LLAMA_CPP_GPU_LAYERS, llama_cpp_concurrency=LLM_LLAMA_CPP_CONCURRENCY, vllm_enforce_eager=EMBEDDING_VLLM_ENFORCE_EAGER, start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)
    llm_block = build_docker_compose(llm_port=LLM_PORT, model_id=LLM_MODEL_ID, embedding=False, max_context_length=LLM_MAX_CONTEXT_LENGTH, runner=LLM_MODEL_RUNNER, gpu_type=LLM_GPU_TYPE, driver=LLM_DRIVER, llama_cpp_gpu_layers=LLM_LLAMA_CPP_GPU_LAYERS, llama_cpp_concurrency=LLM_LLAMA_CPP_CONCURRENCY, vllm_enforce_eager=LLM_VLLM_ENFORCE_EAGER, start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)
    webapp_block = WEBAPP_SETUP.format(webapp_port=WEBAPP_PORT, uvicorn_workers=UVICORN_WORKERS, start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)

    docker_compose_str = DOCKER_COMPOSE_TPL.format(
        postgres_setup=postgres_block.lstrip('\n').rstrip('\n'),
        etcd_setup=etcd_block.lstrip('\n').rstrip('\n'),
        seaweedfs_setup=seaweedfs_block.lstrip('\n').rstrip('\n'),
        milvus_setup=milvus_block.lstrip('\n').rstrip('\n'),
        embedding_setup=embedding_block.lstrip('\n').rstrip('\n'),
        llm_setup=llm_block.lstrip('\n').rstrip('\n'),
        webapp_setup=webapp_block.lstrip('\n').rstrip('\n')
    )
    
    shell_entrypoint_str = SHELL_ENTRYPOINT.format(webapp_port=WEBAPP_PORT, uvicorn_workers=UVICORN_WORKERS).lstrip('\n').rstrip('\n')

    with open("docker-compose.yml", "w") as f:
        f.write(docker_compose_str)

    with open("webapp_entrypoint.sh", "w") as f:
      f.write(shell_entrypoint_str)