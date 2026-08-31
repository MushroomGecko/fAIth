# fAIth - AI-Powered Study Bible

## What is fAIth?
fAIth is an open-source AI-powered study Bible that supercharges your Bible-reading experience. Take notes on what you read, highlight verses, ask questions, and get quizzed to test your knowledge all in one place!

## If using CUDA (NVIDIA 580.XX+ Drivers)
Modern NVIDIA drivers (580.XX+) have deprecated the "legacy" hook mode. To use GPUs with Docker Compose, you must switch to the CDI (Container Device Interface) runtime.

### 1. Configure the Docker Runtime
```
sudo nvidia-ctk runtime configure --runtime=docker
```

### 2. Generate the CDI Device Map
```
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
```

### 3. Enable the CDI Mode and Restart Docker
```
sudo nvidia-ctk config --in-place --set nvidia-container-runtime.mode=cdi && sudo systemctl restart docker
```

**IMPORTANT**: Ensure your `docker-compose.yml` uses `driver: cdi` and `nvidia.com/gpu=all` for device reservations. Legacy driver: nvidia blocks will trigger an OCI runtime error in CDI mode.

## Steps to run fAIth
1. Go into the fAIth directory with `cd fAIth`
2. Make a venv with `python -m venv .venv`
3. Activate the venv with `.venv/bin/activate`
4. Install required packages with `pip install -r requirements.txt`
5. Copy `.env_template` to `.env`
6. Change `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `MILVUS_PASSWORD`, and `SEARXNG_SECRET` in the new `.env` file to use more secure secrets. You can generate secure values with:
   - `DJANGO_SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
   - `POSTGRES_PASSWORD`, `MILVUS_PASSWORD`, and `SEARXNG_SECRET`: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
7. (Optional) Set `HF_TOKEN` if you wish to use models from HuggingFace that require authentication
8. If you wish to host fAIth on your local network, add your local IP to the `DJANGO_ALLOWED_HOSTS` list
9. Configure the remaining `.env` settings to fit your environment:
   - **AI Models**: Set `EMBEDDING_MODEL_ID` and `LLM_MODEL_ID` based on your available memory
   - **Model Serving** - Choose one approach:
     - **Local Models**: Set `EMBEDDING_MODEL_RUNNER` and `LLM_MODEL_RUNNER` (vllm, llama_cpp, ollama, or sglang), configure `EMBEDDING_GPU_TYPE` and `LLM_GPU_TYPE` (cpu, nvidia, amd, intel).
        - **Advanced**: If using llama_cpp, you can adjust `EMBEDDING_LLAMA_CPP_GPU_LAYERS` and `LLM_LLAMA_CPP_GPU_LAYERS` for more fine-grained tuning of where the model lives (-1 for all GPU layers, 0 for CPU-only)
     - **Third-Party Providers**: Set `BASE_EMBEDDING_URL` and `BASE_LLM_URL` instead, then add API keys `EMBEDDING_API_KEY` and `LLM_API_KEY` as needed
   - **Webapp Settings**: `WEBAPP_PORT` and `UVICORN_WORKERS`
   - **Bible Configuration**: `ENABLED_VERSIONS`, `DEFAULT_VERSION`, `DEFAULT_BOOK`, and `DEFAULT_CHAPTER`

**NOTE: Before running fAIth, if you plan to use the default options provided in the `.env` file, please ensure you have at least 6GB of available VRAM or shared system memory to provide ample room for the AI models used. If you do not have at least 6GB of memory, please edit the `.env` file to use models that support your memory size or opt for third-party providers instead.**

10. Run the Docker Compose generator with `python ./scripts/build_docker_compose.py`
11. Start fAIth by running `docker compose up -d`. You may want to use this time to grab a coffee and/or read your Bible. This step may take a while. This step involves downloading all of the required Docker containers, downloading the AI models, and loading the vector database. After these steps complete, fAIth should automatically run via uvicorn.
12. Visit `http://localhost:8000` to access fAIth

## Credits
### Applications
- Docker
   - Accelerated Container Application Development. Docker. (2026, August 18). https://www.docker.com/ 
- Python
   - Welcome to Python.org. Python.org. (n.d.). https://www.python.org/ 
### Bibles
- Berean Standard Bible (BSB)
   - About the berean standard bible. Berean Standard Bible. (n.d.). https://berean.bible/ 
- World English Bible (WEB)
   - World English bible. World English Bible. (n.d.). https://worldenglish.bible/ 
### Dictionaries
- Open English WordNet (Up-to-date Fork of Princeton WordNet)
   - McCrae, J. P., Rademaker, A., Bond, F., Rudnicka, E., & Fellbaum, C. (2019). English WordNet 2019 — An Open-Source WordNet for English. https://aclanthology.org/2019.gwc-1.31
   - Open english wordnet. Open English Wordnet. (n.d.). https://en-word.net/ 
   - https://github.com/globalwordnet/english-wordnet
- Princeton WordNet (Base Dictionary)
   - George A. Miller (1995). WordNet: A Lexical Database for English. Communications of the ACM Vol. 38, No. 11: 39-41.
   - Christiane Fellbaum (1998, ed.) WordNet: An Electronic Lexical Database. Cambridge, MA: MIT Press.
   - Princeton University "About WordNet." WordNet. Princeton University. 2010.
   - Princeton University. (n.d.). WordNet. https://wordnet.princeton.edu/ 
### Docker Containers
#### AI Model Runners
- Docker Model Runner
   - Docker. (2025). model-runner. GitHub. Retrieved August 30, 2026, from https://github.com/docker/model-runner
- llama.cpp
   - ggml. (2023). llama.cpp. GitHub. Retrieved August 30, 2026, from https://github.com/ggml-org/llama.cpp
- Ollama
   - Ollama. (2023). ollama. GitHub. Retrieved August 30, 2026, from https://github.com/ollama/ollama
- SGLang
   - sgl-project. (2024). sglang. GitHub. Retrieved August 30, 2026, from https://github.com/sgl-project/sglang
- vLLM
   - vLLM. (2023). vllm. GitHub. Retrieved August 30, 2026, from https://github.com/vllm-project/vllm
#### Databases
- Milvus (Vector Database)
   - Project, T. M. (2019). milvus. GitHub. Retrieved August 30, 2026, from https://github.com/milvus-io/milvus
- Postgres (User database)
   - PostgreSQL. (2010). postgres. GitHub. Retrieved August 30, 2026, from https://github.com/postgres/postgres
#### Other
- AWS CLI (S3 bucket initializer)
   - https://github.com/aws/aws-cli
- etcd (Milvus metadata storage)
   - etcd-io. (2013). etcd. GitHub. Retrieved August 30, 2026, from https://github.com/etcd-io/etcd
- Ripgrep (File search tool)
   - Gallant, A. (2016). ripgrep. GitHub. Retrieved August 30, 2026, from https://github.com/BurntSushi/ripgrep
- SearXNG (Metasearch engine)
   - SearXNG.org. (2021). searxng. GitHub. Retrieved August 30, 2026, from https://github.com/searxng/searxng
- SeaweedFS (S3-compatible database)
   - SeaweedFS. (2014). seaweedfs. GitHub. Retrieved August 30, 2026, from https://github.com/seaweedfs/seaweedfs
- Valkey (Cache / rate limiter)
   - Valkey. (2024). valkey. GitHub. Retrieved August 30, 2026, from https://github.com/valkey-io/valkey
### Python Libraries
- Django
   - Django. (2012). django. GitHub. Retrieved August 30, 2026, from https://github.com/django/django
- Django ASGI Lifespan (Django ASGI Handler with Lifespan protocol support)
   - Dohnal, V. (2022). django-asgi-lifespan. GitHub. Retrieved August 30, 2026, from https://github.com/illagrenan/django-asgi-lifespan
- Django Ninja (REST Framework)
   - Kucheryaviy, V. (2020). django-ninja. GitHub. Retrieved August 30, 2026, from https://github.com/vitalik/django-ninja
- HTTPX (Async HTTP client)
   - Encode. (2019). httpx. GitHub. Retrieved August 30, 2026, from https://github.com/encode/httpx
- psycopg (Postgres API Library)
   - Team, T. P. (2020). psycopg. GitHub. Retrieved August 30, 2026, from https://github.com/psycopg/psycopg
- PyMilvus (Mivlus API Library)
   - Project, T. M. (2019). pymilvus. GitHub. Retrieved August 30, 2026, from https://github.com/milvus-io/pymilvus
- Python Markdown (Markdown to HTML renderer)
   - Python-Markdown. (2010). markdown. GitHub. Retrieved August 30, 2026, from https://github.com/Python-Markdown/markdown
- Python OpenAI API Library
   - OpenAI. (2020). openai-python. GitHub. Retrieved August 30, 2026, from https://github.com/openai/openai-python
- python-dotenv (Environment Variable Loader)
   - Kumar, S. (2014). python-dotenv. GitHub. Retrieved August 30, 2026, from https://github.com/theskumar/python-dotenv
- Python WordNet (Python Interface for Open English WordNet)
   - Goodman, M. W., & Bond, F. (2021). Intrinsically Interlingual: The Wn Python Library for Wordnets [Conference paper]. 100–107. https://aclanthology.org/2021.gwc-1.12/
   - Goodman, M. W. & Bond, F. (n.d.). Wn. GitHub. Retrieved August 30, 2026, from https://github.com/goodmami/wn/
- Uvicorn (ASGI Runner) - https://github.com/Kludex/uvicorn
   - Trylesinski, M., & Christie, T. Uvicorn [Computer software]. https://github.com/Kludex/uvicorn
- WhiteNoise (Static file serving)
   - Evans, D. (2013). whitenoise. GitHub. Retrieved August 30, 2026, from https://github.com/evansd/whitenoise

## Licensing
fAIth is released under the GNU General Public License v3.0 (GPLv3). We believe that just as God's Word is a gift freely given to all, the tools used to interact with it should remain free for everyone to use, study, and share.

The GPL ensures that fAIth remains a community resource. By mandating that all modifications remain open source, we guarantee that no one can restrict access to this project. This transparency allows the community to audit the code, ensuring that the software remains safe, authentic, and true to its purpose of helping users grow closer to God.
