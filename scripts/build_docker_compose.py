import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is on sys.path when running this script directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

# Milvus specific things
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")

# Hugging Face specific things
HF_TOKEN = os.getenv("HF_TOKEN", "")

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
{milvus_setup}
{embedding_setup}
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

MILVUS_SETUP = \
"""
  etcd:
    container_name: milvus-etcd-faith
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
    container_name: milvus-minio-faith
    image: minio/minio:latest
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
      MINIO_LOG_LEVEL: warn
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/minio:/minio_data
    command: minio server /minio_data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  milvus:
    container_name: milvus-faith
    image: milvusdb/milvus:latest
    ports:
      - "{milvus_port}:{milvus_port}"
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - ${{DOCKER_VOLUME_DIRECTORY:-.}}/volumes/milvus:/var/lib/milvus
    command: ["milvus", "run", "standalone"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      interval: 30s
      start_period: 90s
      timeout: 20s
      retries: 3
    security_opt:
      - seccomp:unconfined
    depends_on:
      - "etcd"
      - "minio"
""".lstrip('\n')

OLLAMA_SETUP = \
"""
  ollama_{model_type}:
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
      interval: 30s
      timeout: 10s
      retries: 5
{gpu_setup}
""".lstrip('\n')

LLAMA_CPP_SETUP = \
"""
  llama_cpp_{model_type}:
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
    command: ["-hf", "{model_id}", "-c", "{max_context_length}", "-ngl", "{llama_cpp_gpu_layers}", "--cache-type-k", "q8_0", "--cache-type-v", "q8_0", "--host", "0.0.0.0", "--port", "{llm_port}", {embedding}]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{llm_port}/health"]
      interval: 30s
      timeout: 10s
      retries: 5
{gpu_setup}
""".lstrip('\n')

VLLM_SETUP = \
"""
  vllm_{model_type}:
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
      interval: 30s
      timeout: 10s
      retries: 5
{gpu_setup}
""".lstrip('\n')

SGLANG_SETUP = \
"""
  sglang_{model_type}:
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
      interval: 30s
      timeout: 10s
      retries: 5
{gpu_setup}
""".lstrip('\n')

def build_docker_compose(llm_port, model_id, embedding, max_context_length, runner, gpu_type, driver,  llama_cpp_gpu_layers, vllm_enforce_eager):
    """Build the docker compose file."""
    if embedding:
        embedding_setup = "--embedding"
        model_type = "embedding"
    else:
        embedding_setup = None
        model_type = "llm"
    
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
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, gpu_setup="", ollama_force_cpu="OLLAMA_NUM_GPU=0", ollama_image="ollama/ollama:latest", model_type=model_type)
        elif runner == "llama_cpp":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup="", llama_cpp_gpu_layers=llama_cpp_gpu_layers, llama_cpp_image="ghcr.io/ggml-org/llama.cpp:server", hf_token=HF_TOKEN, embedding=embedding_setup, model_type=model_type)
        elif runner == "vllm":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup="", vllm_enforce_eager=vllm_enforce_eager, hf_token=HF_TOKEN, vllm_image="vllm/vllm-openai:latest", model_type=model_type)
        elif runner == "sglang":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup="", hf_token=HF_TOKEN, sglang_image="lmsysorg/sglang:latest", model_type=model_type)
        else:
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATBILITY_LIST}")
    
    elif driver == "cuda":
        if gpu_type != "nvidia":
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATBILITY_LIST}")

        if runner == "ollama":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, gpu_setup=NVIDIA_SETUP, ollama_force_cpu="", ollama_image="ollama/ollama:latest", model_type=model_type)
        elif runner == "llama_cpp":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=NVIDIA_SETUP, llama_cpp_gpu_layers=llama_cpp_gpu_layers, llama_cpp_image="ghcr.io/ggml-org/llama.cpp:server-cuda", hf_token=HF_TOKEN, embedding=embedding_setup, model_type=model_type)
        elif runner == "vllm":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=NVIDIA_SETUP, vllm_enforce_eager=vllm_enforce_eager, hf_token=HF_TOKEN, vllm_image="vllm/vllm-openai:latest", model_type=model_type)
        elif runner == "sglang":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=NVIDIA_SETUP, hf_token=HF_TOKEN, sglang_image="lmsysorg/sglang:latest", model_type=model_type)
        else:
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`")
    
    elif driver == "rocm":
        if gpu_type != "amd":
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATBILITY_LIST}")

        if runner == "ollama":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, gpu_setup=ROCM_SETUP, ollama_force_cpu="", ollama_image="ollama/ollama:rocm", model_type=model_type)
        elif runner == "llama_cpp":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=ROCM_SETUP, llama_cpp_gpu_layers=llama_cpp_gpu_layers, llama_cpp_image="ghcr.io/ggml-org/llama.cpp:server-rocm", hf_token=HF_TOKEN, embedding=embedding_setup, model_type=model_type)
        elif runner == "vllm":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=ROCM_SETUP, vllm_enforce_eager=vllm_enforce_eager, hf_token=HF_TOKEN, vllm_image="rocm/vllm:latest", model_type=model_type)
        elif runner == "sglang":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=ROCM_SETUP, hf_token=HF_TOKEN, sglang_image="lmsysorg/sglang:dsv32-rocm", model_type=model_type)
        else:
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATBILITY_LIST}")
    
    elif driver == "vulkan":
        if gpu_type == "cpu":
            raise ValueError(f"Invalid driver `{driver}` with GPU type `{gpu_type}`. Please check the compatibility list:\n{COMPATBILITY_LIST}")

        if runner == "llama_cpp":
            runner_setup = runner_setup.format(llm_port=llm_port, model_id=model_id, max_context_length=max_context_length, gpu_setup=gpu_setup, llama_cpp_gpu_layers=llama_cpp_gpu_layers, llama_cpp_image="ghcr.io/ggml-org/llama.cpp:server-vulkan", hf_token=HF_TOKEN, embedding=embedding_setup, model_type=model_type)
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

    milvus_block = MILVUS_SETUP.format(milvus_port=MILVUS_PORT)
    embedding_block = build_docker_compose(llm_port=EMBEDDING_PORT, model_id=EMBEDDING_MODEL_ID, embedding=True, max_context_length=EMBEDDING_MAX_CONTEXT_LENGTH, runner=EMBEDDING_MODEL_RUNNER, gpu_type=EMBEDDING_GPU_TYPE, driver=EMBEDDING_DRIVER, llama_cpp_gpu_layers=EMBEDDING_LLAMA_CPP_GPU_LAYERS, vllm_enforce_eager=EMBEDDING_VLLM_ENFORCE_EAGER)

    docker_compose_str = DOCKER_COMPOSE_TPL.format(
        milvus_setup=milvus_block,
        embedding_setup=embedding_block,
    )

    with open("docker-compose.yml", "w") as f:
        f.write(docker_compose_str)