import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root is on sys.path when running this script directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

# ============================================================================
# Compatibility Matrix - Shows valid driver/runner/device combinations
# ============================================================================

COMPATIBILITY_LIST = \
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

# ============================================================================
# Docker Compose Template - Main service composition
# ============================================================================

DOCKER_COMPOSE_TPL = """
services:
{services}
""".lstrip('\n')

# ============================================================================
# Helper Function - Builds service list with proper spacing
# ============================================================================

def build_services_section(postgres_setup, etcd_setup, seaweedfs_setup, milvus_setup, embedding_setup, llm_setup, webapp_setup):
    """
    Build the services section of docker-compose with proper spacing.
    
    Only includes services with content, avoiding blank lines for disabled services.
    
    Parameters:
        postgres_setup, etcd_setup, seaweedfs_setup, milvus_setup: Always included
        embedding_setup, llm_setup: Included only if non-empty
        webapp_setup: Always included (final service)
    
    Returns:
        str: Formatted services section
    """
    services = []
    
    # Always include these services
    services.append(postgres_setup.lstrip('\n').rstrip('\n'))
    services.append(etcd_setup.lstrip('\n').rstrip('\n'))
    services.append(seaweedfs_setup.lstrip('\n').rstrip('\n'))
    services.append(milvus_setup.lstrip('\n').rstrip('\n'))
    
    # Conditionally include embedding service
    if embedding_setup.strip():
        services.append(embedding_setup.lstrip('\n').rstrip('\n'))
    
    # Conditionally include LLM service
    if llm_setup.strip():
        services.append(llm_setup.lstrip('\n').rstrip('\n'))
    
    # Always include webapp (final service)
    services.append(webapp_setup.lstrip('\n').rstrip('\n'))
    
    # Join all services with double newline separator (blank line between services)
    return '\n\n'.join(services)

# ============================================================================
# GPU Configuration Templates - Driver/device-specific setup
# ============================================================================

NVIDIA_SETUP = \
"""
    deploy:
      resources:
        reservations:
          devices:
            - driver: cdi
              device_ids:
                - nvidia.com/gpu=all
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

# ============================================================================
# Service Configuration Templates
# ============================================================================

POSTGRES_SETUP = \
"""
  postgres:
    container_name: postgres-faith
    image: postgres:latest
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

# SeaweedFS: distributed file storage for Milvus backups
SEAWEEDFS_SETUP = \
"""
  seaweedfs-master:
    container_name: seaweedfs-master-faith
    image: chrislusf/seaweedfs:4.03
    command: 'master -ip=seaweedfs-master -ip.bind=0.0.0.0 -metricsPort=9324 -mdir=/data'
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/seaweedfs/master:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://seaweedfs-master:9333/cluster/status"]
      interval: {interval}
      timeout: {timeout}
      retries: {retries}

  seaweedfs-volume:
    container_name: seaweedfs-volume-faith
    image: chrislusf/seaweedfs:4.03
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/seaweedfs/volume:/data
    command: 'volume -ip=seaweedfs-volume -master="seaweedfs-master:9333" -ip.bind=0.0.0.0 -port=8080 -metricsPort=9325 -dir=/data'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://seaweedfs-volume:8080/status"]
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
    depends_on:
      seaweedfs-master:
        condition: service_healthy

  seaweedfs-filer:
    container_name: seaweedfs-filer-faith
    image: chrislusf/seaweedfs:4.03
    command: 'filer -ip=seaweedfs-filer -master="seaweedfs-master:9333" -ip.bind=0.0.0.0 -metricsPort=9326'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://seaweedfs-filer:8888/"]
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
    environment:
      AWS_ACCESS_KEY_ID: minioadmin
      AWS_SECRET_ACCESS_KEY: minioadmin
    command: 's3 -filer="seaweedfs-filer:8888" -ip.bind=0.0.0.0 -metricsPort=9327'
    healthcheck:
      test: ["CMD", "curl", "http://seaweedfs-s3:8333/"]
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

# Milvus: vector database for semantic search
def build_milvus_setup(local_embedding_enabled, start_period, interval, timeout, retries):
    """
    Build Milvus configuration with optional embedding dependency.
    
    Milvus only needs to depend on embedding if it's being used for building
    initial collections with embeddings during setup.
    
    Parameters:
        embedding_enabled: True if EMBEDDING_PORT is set
        start_period, interval, timeout, retries: Healthcheck parameters
    
    Returns:
        str: Formatted Milvus Docker Compose service configuration
    """
    # Build depends_on section based on enabled services
    depends_on = """    depends_on:
      etcd:
        condition: service_healthy
      seaweedfs-s3:
        condition: service_healthy
      seaweedfs-init:
        condition: service_completed_successfully"""
    
    # Only depend on embedding if it's enabled (for initial collection building)
    if local_embedding_enabled:
        depends_on += """
      embedding:
        condition: service_healthy"""
    
    milvus_setup = f"""
  milvus:
    container_name: milvus-faith
    image: milvusdb/milvus:latest
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
      test: ["CMD", "curl", "-f", "http://milvus:9091/healthz"]
      start_period: {start_period}
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
    security_opt:
      - seccomp:unconfined
{depends_on}
"""
    return milvus_setup.lstrip('\n')

# ============================================================================
# LLM Runner Configuration Templates - Ollama, llama.cpp, vLLM, SGLang
# ============================================================================

OLLAMA_SETUP = \
"""
  {model_type}:
    container_name: ollama-{model_type}-faith
    image: {ollama_image}
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/ollama:/root/.ollama
    environment:
      OLLAMA_HOST: 0.0.0.0:{llm_port}
      OLLAMA_MODELS: /root/.ollama
      OLLAMA_KEEP_ALIVE: 24h
      {ollama_force_cpu}
    command: ["serve"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://{model_type}:{llm_port}/api/tags"]
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
    environment:
      HF_TOKEN: {hf_token}
      HF_HOME: /root/.cache/huggingface
      HUGGINGFACE_HUB_CACHE: /root/.cache/huggingface
    command: ["-hf", "{model_id}", "-c", "{max_context_length}", "-ngl", "{llama_cpp_gpu_layers}", "--cache-type-k", "q8_0", "--cache-type-v", "q8_0", "--host", "0.0.0.0", "--port", "{llm_port}", "--cont-batching", "-np", "{llama_cpp_concurrency}", {embedding}]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://{model_type}:{llm_port}/health"]
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
    environment:
      HF_TOKEN: {hf_token}
      HF_HOME: /root/.cache/huggingface
      HUGGINGFACE_HUB_CACHE: /root/.cache/huggingface
    command: ["--model", "{model_id}", "--download-dir", "/root/.cache/huggingface", "--max-model-len", "{max_context_length}", "--dtype", "auto", "--enforce-eager", "{vllm_enforce_eager}", "--host", "0.0.0.0", "--port", "{llm_port}"]
    ipc: host
    healthcheck:
      test: ["CMD", "curl", "-f", "http://{model_type}:{llm_port}/health"]
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

# ============================================================================
# Webapp Service Configuration - Built conditionally based on enabled services
# ============================================================================

def build_webapp_setup(
  milvus_enabled,
  milvus_url,
  embedding_enabled,
  embedding_url,
  llm_enabled,
  llm_url,
  webapp_port, 
  uvicorn_workers, 
  django_debug, 
  django_secret_key, 
  django_allowed_hosts, 
  postgres_port, 
  postgres_user, 
  postgres_password, 
  postgres_database, 
  start_period, 
  interval, 
  timeout, 
  retries):
    """
    Build webapp configuration with conditional service dependencies.
    
    If embedding or LLM services are not enabled (ports not set), the webapp
    will use external services (e.g., OpenAI, OpenRouter) configured via .env.
    
    Parameters:
        milvus_enabled (bool): True if MILVUS_PORT is set
        milvus_url: Complete Milvus URL
        embedding_enabled (bool): True if EMBEDDING_PORT is set
        llm_enabled (bool): True if LLM_PORT is set
        webapp_port: Port to expose webapp on
        uvicorn_workers: Number of uvicorn workers
        django_debug: Django debug mode
        django_secret_key: Django secret key
        django_allowed_hosts: Django allowed hosts
        postgres_port: Postgres port
        postgres_user: Postgres user
        start_period, interval, timeout, retries: Healthcheck parameters
    
    Returns:
        str: Formatted webapp Docker Compose service configuration
    """
    # Build depends_on section based on enabled services
    depends_on = """    depends_on:
      postgres:
        condition: service_healthy
    """
    
    if milvus_enabled:
        depends_on += """
      milvus:
        condition: service_healthy"""
    
    if embedding_enabled:
        depends_on += """
      embedding:
        condition: service_healthy"""
    
    if llm_enabled:
        depends_on += """
      llm:
        condition: service_healthy"""
    
    webapp_setup = f"""
  webapp:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: webapp-faith
    ports:
      - "{webapp_port}:8000"
    env_file:
      - .env
    environment:
      DJANGO_DEBUG: {django_debug}
      DJANGO_SECRET_KEY: '{django_secret_key}'
      DJANGO_ALLOWED_HOSTS: '{django_allowed_hosts}'
      POSTGRES_HOST: postgres
      POSTGRES_PORT: {postgres_port}
      POSTGRES_USER: {postgres_user}
      POSTGRES_PASSWORD: {postgres_password}
      POSTGRES_DATABASE: {postgres_database}
      MILVUS_URL: {milvus_url}
      BASE_EMBEDDING_URL: {embedding_url}
      BASE_LLM_URL: {llm_url}
    command: sh -c "python scripts/docker_milvus_initializer.py && python manage.py migrate && python manage.py collectstatic --noinput --clear && uvicorn fAIth.asgi:application --host 0.0.0.0 --port 8000 --workers {uvicorn_workers}"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://webapp:8000/healthcheck/"]
      start_period: {start_period}
      interval: {interval}
      timeout: {timeout}
      retries: {retries}
{depends_on}
    volumes:
      - .:/app
"""
    return webapp_setup.lstrip('\n')

# ============================================================================
# Shell Entrypoint Script - Alternative startup sequence with permissions
# ============================================================================

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

# ============================================================================
# Main Function - Builds runner configuration based on driver/runner/device
# ============================================================================

def build_docker_compose(llm_port, model_id, embedding, max_context_length, runner, gpu_type, driver, llama_cpp_gpu_layers, llama_cpp_concurrency, vllm_enforce_eager, hf_token, start_period, interval, timeout, retries):
    """
    Build the docker compose configuration for LLM or embedding service.

    Selects the appropriate template and GPU setup based on runner and driver choice.
    Validates compatibility and formats the configuration with provided parameters.

    Parameters:
        llm_port: Port to expose the service on
        model_id: HuggingFace model identifier
        embedding: True for embedding service, False for LLM
        max_context_length: Maximum context window for the model
        runner: Model runner type (ollama, llama_cpp, vllm, sglang)
        gpu_type: GPU type (cpu, nvidia, amd, intel)
        driver: ML framework driver (cpu, cuda, rocm, vulkan)
        llama_cpp_gpu_layers: Number of layers to offload to GPU (llama.cpp)
        llama_cpp_concurrency: Number of concurrent requests (llama.cpp)
        vllm_enforce_eager: Enforce eager execution mode (vLLM)
        hf_token: HuggingFace API token for model access
        start_period, interval, timeout, retries: Healthcheck parameters

    Returns:
        str: Formatted Docker Compose service configuration
    """
    # Determine if building embedding or LLM service
    embedding_setup = '"--embedding"' if embedding else ''
    model_type = "embedding" if embedding else "llm"
    
    # Select template based on runner type
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

    # Select GPU setup template based on GPU type
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
    
    # ========================================================================
    # CPU Driver - Uses software-based inference
    # ========================================================================
    
    if driver == "cpu":
        # Warn if user specified GPU type but selected CPU driver
        if gpu_type != "cpu":
            if embedding:
                print(f"WARNING: Using CPU driver with GPU type `{gpu_type}`. If this is not intended, please check your `EMBEDDING_DRIVER` environment variable.")
            else:
                print(f"WARNING: Using CPU driver with GPU type `{gpu_type}`. If this is not intended, please check your `LLM_DRIVER` environment variable.")

        # Format runner template with CPU-specific configuration
        if runner == "ollama":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, gpu_setup="", ollama_force_cpu="OLLAMA_NUM_GPU=0", ollama_image="ollama/ollama:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "llama_cpp":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup="", llama_cpp_gpu_layers=llama_cpp_gpu_layers, llama_cpp_image="ghcr.io/ggml-org/llama.cpp:server", hf_token=hf_token, embedding=embedding_setup, llama_cpp_concurrency=llama_cpp_concurrency, model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "vllm":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup="", vllm_enforce_eager=vllm_enforce_eager, hf_token=hf_token, vllm_image="vllm/vllm-openai:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "sglang":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup="", hf_token=hf_token, sglang_image="lmsysorg/sglang:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        else:
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATIBILITY_LIST}")
    
    # ========================================================================
    # CUDA Driver - NVIDIA GPU acceleration
    # ========================================================================
    
    elif driver == "cuda":
        # Validate CUDA only works with NVIDIA GPUs
        if gpu_type != "nvidia":
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATIBILITY_LIST}")

        # Format runner templates with CUDA GPU support
        if runner == "ollama":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, gpu_setup=NVIDIA_SETUP, ollama_force_cpu="", ollama_image="ollama/ollama:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "llama_cpp":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=NVIDIA_SETUP, llama_cpp_gpu_layers=llama_cpp_gpu_layers, llama_cpp_image="ghcr.io/ggml-org/llama.cpp:server-cuda", hf_token=hf_token, embedding=embedding_setup, llama_cpp_concurrency=llama_cpp_concurrency, model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "vllm":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=NVIDIA_SETUP, vllm_enforce_eager=vllm_enforce_eager, hf_token=hf_token, vllm_image="vllm/vllm-openai:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "sglang":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=NVIDIA_SETUP, hf_token=hf_token, sglang_image="lmsysorg/sglang:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        else:
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`")
    
    # ========================================================================
    # ROCM Driver - AMD GPU acceleration
    # ========================================================================
    
    elif driver == "rocm":
        # Validate ROCM only works with AMD GPUs
        if gpu_type != "amd":
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATIBILITY_LIST}")

        # Format runner templates with ROCM GPU support
        if runner == "ollama":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, gpu_setup=AMD_SETUP, ollama_force_cpu="", ollama_image="ollama/ollama:rocm", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "llama_cpp":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=AMD_SETUP, llama_cpp_gpu_layers=llama_cpp_gpu_layers, llama_cpp_image="ghcr.io/ggml-org/llama.cpp:server-rocm", hf_token=hf_token, embedding=embedding_setup, llama_cpp_concurrency=llama_cpp_concurrency, model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "vllm":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=AMD_SETUP, vllm_enforce_eager=vllm_enforce_eager, hf_token=hf_token, vllm_image="rocm/vllm:latest", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        elif runner == "sglang":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=AMD_SETUP, hf_token=hf_token, sglang_image="lmsysorg/sglang:dsv32-rocm", model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        else:
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATIBILITY_LIST}")
    
    # ========================================================================
    # VULKAN Driver - Cross-platform GPU acceleration
    # ========================================================================
    
    elif driver == "vulkan":
        # Validate VULKAN doesn't support CPU
        if gpu_type == "cpu":
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATIBILITY_LIST}")

        # Only llama.cpp supports VULKAN currently
        if runner == "llama_cpp":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=gpu_setup, llama_cpp_gpu_layers=llama_cpp_gpu_layers, llama_cpp_image="ghcr.io/ggml-org/llama.cpp:server-vulkan", hf_token=hf_token, embedding=embedding_setup, llama_cpp_concurrency=llama_cpp_concurrency, model_type=model_type, start_period=start_period, interval=interval, timeout=timeout, retries=retries)
        else:
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATIBILITY_LIST}")
    
    else:
        raise ValueError(f"Invalid driver: `{driver}`. Please check the compatibility list:\n{COMPATIBILITY_LIST}")

    print(f"Using `{runner}` with GPU type `{gpu_type}` on driver `{driver}`")
    return runner_setup

# ============================================================================
# Main Entry Point - Generates docker-compose.yml and entrypoint script
# ============================================================================

if __name__ == "__main__":
    # ========================================================================
    # Load All Configuration from Environment Variables
    # ========================================================================
    
    # Webapp configuration
    WEBAPP_PORT = int(str(os.getenv("WEBAPP_PORT", 8000)).strip())
    UVICORN_WORKERS = int(str(os.getenv("UVICORN_WORKERS", 1)).strip())
    
    # Postgres configuration
    POSTGRES_HOST = str(os.getenv("POSTGRES_HOST", "")).strip()
    DEFAULT_POSTGRES_PORT = "5432"
    POSTGRES_PORT = str(os.getenv("POSTGRES_PORT", DEFAULT_POSTGRES_PORT)).strip()
    POSTGRES_USER = str(os.getenv("POSTGRES_USER", "faith_user")).strip()
    POSTGRES_PASSWORD = str(os.getenv("POSTGRES_PASSWORD", "postgres-secure-password")).strip()
    POSTGRES_DATABASE = str(os.getenv("POSTGRES_DATABASE", "faith_db")).strip()
    
    # Milvus configuration
    MILVUS_URL = str(os.getenv("MILVUS_URL", "")).strip()
    DEFAULT_MILVUS_PORT = "19530"
    
    # Embedding configuration
    EMBEDDING_PORT = str(os.getenv("EMBEDDING_PORT", "")).strip()
    BASE_EMBEDDING_URL = str(os.getenv("BASE_EMBEDDING_URL", "")).strip()
    EMBEDDING_MODEL_ID = str(os.getenv("EMBEDDING_MODEL_ID", "Qwen/Qwen3-Embedding-0.6B")).strip()
    EMBEDDING_MAX_CONTEXT_LENGTH = int(str(os.getenv("EMBEDDING_MAX_CONTEXT_LENGTH", 4096)).strip())
    EMBEDDING_MODEL_RUNNER = str(os.getenv("EMBEDDING_MODEL_RUNNER", "llama_cpp")).strip()
    EMBEDDING_GPU_TYPE = str(os.getenv("EMBEDDING_GPU_TYPE", "cpu")).strip()
    EMBEDDING_DRIVER = str(os.getenv("EMBEDDING_DRIVER", "cpu")).strip()
    EMBEDDING_VLLM_ENFORCE_EAGER = str(os.getenv("EMBEDDING_VLLM_ENFORCE_EAGER", "False")).strip()
    EMBEDDING_LLAMA_CPP_GPU_LAYERS = int(str(os.getenv("EMBEDDING_LLAMA_CPP_GPU_LAYERS", 0)).strip())
    # Special case: -1 means offload all layers (set to 9999 to effectively offload all)
    if EMBEDDING_LLAMA_CPP_GPU_LAYERS == -1:
        EMBEDDING_LLAMA_CPP_GPU_LAYERS = 9999
    EMBEDDING_LLAMA_CPP_CONCURRENCY = int(str(os.getenv("EMBEDDING_LLAMA_CPP_CONCURRENCY", 2)).strip())
    
    # LLM configuration
    LLM_PORT = str(os.getenv("LLM_PORT", "")).strip()
    BASE_LLM_URL = str(os.getenv("BASE_LLM_URL", "")).strip()
    LLM_MODEL_ID = str(os.getenv("LLM_MODEL_ID", "unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M")).strip()
    LLM_MAX_CONTEXT_LENGTH = int(str(os.getenv("LLM_MAX_CONTEXT_LENGTH", 4096)).strip())
    LLM_MODEL_RUNNER = str(os.getenv("LLM_MODEL_RUNNER", "llama_cpp")).strip()
    LLM_GPU_TYPE = str(os.getenv("LLM_GPU_TYPE", "cpu")).strip()
    LLM_DRIVER = str(os.getenv("LLM_DRIVER", "cpu")).strip()
    LLM_LLAMA_CPP_GPU_LAYERS = int(str(os.getenv("LLM_LLAMA_CPP_GPU_LAYERS", 0)).strip())
    # Special case: -1 means offload all layers (set to 9999 to effectively offload all)
    if LLM_LLAMA_CPP_GPU_LAYERS == -1:
        LLM_LLAMA_CPP_GPU_LAYERS = 9999
    LLM_LLAMA_CPP_CONCURRENCY = int(str(os.getenv("LLM_LLAMA_CPP_CONCURRENCY", 2)).strip())
    LLM_VLLM_ENFORCE_EAGER = str(os.getenv("LLM_VLLM_ENFORCE_EAGER", "False")).strip()
    
    # Django configuration
    DJANGO_DEBUG = str(os.getenv("DJANGO_DEBUG", "False")).strip()
    DJANGO_SECRET_KEY = str(os.getenv("DJANGO_SECRET_KEY", "django-insecure-d)+b7f#u@$@q)(ft*qcz1!%^uvy(_ext-^t4d6i$3l$)21__s(")).strip()
    DJANGO_ALLOWED_HOSTS = str(os.getenv("DJANGO_ALLOWED_HOSTS", "[\"127.0.0.1\", \"localhost\"]")).strip()
    print(f"DJANGO_ALLOWED_HOSTS: {DJANGO_ALLOWED_HOSTS}")
    
    # HuggingFace configuration
    HF_TOKEN = str(os.getenv("HF_TOKEN", "")).strip()
    
    # Healthcheck configuration
    START_PERIOD = "3600s"
    INTERVAL = "30s"
    TIMEOUT = "30s"
    RETRIES = 5

    # ========================================================================
    # Determine Which Services Are Enabled (Based on Port Configuration)
    # ========================================================================
    
    # Services are only included if their ports are explicitly set
    # If port is empty, user will configure external service (e.g., OpenAI, OpenRouter)
    local_postgres_enabled = not bool(POSTGRES_HOST.strip())
    local_milvus_enabled = not bool(MILVUS_URL.strip())
    local_embedding_enabled = not bool(BASE_EMBEDDING_URL.strip())
    local_llm_enabled = not bool(BASE_LLM_URL.strip())

    if local_postgres_enabled:
        print("INFO: POSTGRES_HOST not set. Webapp will use local PostgreSQL service (configure POSTGRES_HOST in .env)")
    postgres_host = "postgres" if local_postgres_enabled else POSTGRES_HOST.replace("http://", "").replace("https://", "")
    postgres_port = "5432" if local_postgres_enabled else POSTGRES_PORT
    
    if local_milvus_enabled:
        print("INFO: MILVUS_URL not set. Webapp will use local Milvus service (configure MILVUS_URL in .env)")
    milvus_url = f"http://milvus:{DEFAULT_MILVUS_PORT}" if local_milvus_enabled else MILVUS_URL
    
    if local_embedding_enabled:
        print("INFO: BASE_EMBEDDING_URL not set. Webapp will use local embedding service (configure BASE_EMBEDDING_URL in .env)")
    embedding_url = f"http://embedding:{EMBEDDING_PORT}/v1" if local_embedding_enabled else BASE_EMBEDDING_URL

    if local_llm_enabled:
        print("INFO: BASE_LLM_URL not set. Webapp will use local LLM service (configure BASE_LLM_URL in .env)")
    llm_url = f"http://llm:{LLM_PORT}/v1" if local_llm_enabled else BASE_LLM_URL
    
    # ========================================================================
    # Format Service Configuration Blocks
    # ========================================================================
    
    if local_postgres_enabled:
        postgres_block = POSTGRES_SETUP.format(postgres_host=postgres_host, postgres_port=postgres_port, postgres_user=POSTGRES_USER, postgres_password=POSTGRES_PASSWORD, postgres_database=POSTGRES_DATABASE, start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)
    else:
        postgres_block = ""
    
    # Build Milvus block with conditional embedding dependency
    if local_milvus_enabled:
        etcd_block = ETCD_SETUP.format(start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)
        seaweedfs_block = SEAWEEDFS_SETUP.format(start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)
        milvus_block = build_milvus_setup(local_embedding_enabled=local_embedding_enabled, start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)
    else:
        etcd_block = ""
        seaweedfs_block = ""
        milvus_block = ""
    
    # Build embedding service block only if port is set
    if local_embedding_enabled:
        embedding_block = build_docker_compose(llm_port=EMBEDDING_PORT, model_id=EMBEDDING_MODEL_ID, embedding=True, max_context_length=EMBEDDING_MAX_CONTEXT_LENGTH, runner=EMBEDDING_MODEL_RUNNER, gpu_type=EMBEDDING_GPU_TYPE, driver=EMBEDDING_DRIVER, llama_cpp_gpu_layers=EMBEDDING_LLAMA_CPP_GPU_LAYERS, llama_cpp_concurrency=EMBEDDING_LLAMA_CPP_CONCURRENCY, vllm_enforce_eager=EMBEDDING_VLLM_ENFORCE_EAGER, hf_token=HF_TOKEN, start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)
    else:
        embedding_block = ""
    
    # Build LLM service block only if port is set
    if local_llm_enabled:
        llm_block = build_docker_compose(llm_port=LLM_PORT, model_id=LLM_MODEL_ID, embedding=False, max_context_length=LLM_MAX_CONTEXT_LENGTH, runner=LLM_MODEL_RUNNER, gpu_type=LLM_GPU_TYPE, driver=LLM_DRIVER, llama_cpp_gpu_layers=LLM_LLAMA_CPP_GPU_LAYERS, llama_cpp_concurrency=LLM_LLAMA_CPP_CONCURRENCY, vllm_enforce_eager=LLM_VLLM_ENFORCE_EAGER, hf_token=HF_TOKEN, start_period=START_PERIOD, interval=INTERVAL, timeout=TIMEOUT, retries=RETRIES)
    else:
        llm_block = ""
    
    # Build webapp with conditional dependencies based on enabled services
    webapp_block = build_webapp_setup(
        milvus_enabled=local_milvus_enabled,
        milvus_url=milvus_url,
        embedding_enabled=local_embedding_enabled,
        embedding_url=embedding_url,
        llm_enabled=local_llm_enabled,
        llm_url=llm_url,
        webapp_port=WEBAPP_PORT,
        uvicorn_workers=UVICORN_WORKERS,
        django_debug=DJANGO_DEBUG,
        django_secret_key=DJANGO_SECRET_KEY,
        django_allowed_hosts=DJANGO_ALLOWED_HOSTS,
        postgres_port=postgres_port,
        postgres_user=POSTGRES_USER,
        postgres_password=POSTGRES_PASSWORD,
        postgres_database=POSTGRES_DATABASE,
        start_period=START_PERIOD, 
        interval=INTERVAL, 
        timeout=TIMEOUT, 
        retries=RETRIES)

    # ========================================================================
    # Assemble Final Docker Compose Configuration
    # ========================================================================
    
    # Build services section with proper spacing (no gaps for disabled services)
    services_section = build_services_section(
        postgres_setup=postgres_block,
        etcd_setup=etcd_block,
        seaweedfs_setup=seaweedfs_block,
        milvus_setup=milvus_block,
        embedding_setup=embedding_block,
        llm_setup=llm_block,
        webapp_setup=webapp_block
    )
    
    docker_compose_str = DOCKER_COMPOSE_TPL.format(services=services_section)
    
    # Prepare shell entrypoint script with proper formatting
    shell_entrypoint_str = SHELL_ENTRYPOINT.format(webapp_port=WEBAPP_PORT, uvicorn_workers=UVICORN_WORKERS).lstrip('\n').rstrip('\n')

    # ========================================================================
    # Write Generated Files
    # ========================================================================
    
    with Path("docker-compose.yml").open("w", encoding="utf-8") as f:
        f.write(docker_compose_str)

    with Path("webapp_entrypoint.sh").open("w", encoding="utf-8") as f:
        f.write(shell_entrypoint_str)