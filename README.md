# fAIth - AI-Powered Study Bible

## What is fAIth?
fAIth is an open-source study Bible that supercharges your Bible-reading experience. Take notes on what you read, highlight verses, ask questions, and get quizzed to test your knowledge all in one place!

## If using CUDA
The current version of Nvidia 580.XX breaks and no longer supports legacy mode. Use the CDI runtime instead.

```
> sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
> sudo nvidia-ctk config --in-place --set nvidia-container-runtime.mode=cdi && systemctl restart docker
```

## Steps to run fAIth
1. Go into the fAIth directory with `cd fAIth`
2. Make a venv with `python -m venv .`
3. Activate the venv with `./bin/activate`
4. Install required packages with `pip install -r requirements.txt`
5. Copy `.env_template` to `.env`
6. Edit `.env` to fit your environment

**NOTE: Before running fAIth, if you plan to use the default options provided in the `.env` file, please ensure you have at least 6GB of available VRAM or shared system memory to provide ample room for the AI models used. If you do not have at least 6GB of memory, please edit the `.env` file to use models that support your memory size.**

7. Run the Docker YML generator with `python ./scripts/build_docker_compose`
8. Start fAIth by running `docker compose up -d`. You may want to use this time to grab a coffee and/or read your Bible. This step may take a while. This step involves downloading all of the required Docker containers, downloading the AI models, and loading the vector database. After these steps complete, fAIth should automatically run via uvicorn.
9. Visit `http://localhost:8000` to access fAIth

## Credits
### Applications
- Python - https://www.python.org/
- Docker - https://www.docker.com/
### Bibles
- World English Bible (WEB) - https://worldenglish.bible/
- Berean Standard Bible (BSB) - https://berean.bible/
### Python Libraries
- Django - https://github.com/django/django
- Django Rest Framework (DRF) - https://github.com/encode/django-rest-framework
- Async Django Rest Framework (aDRF) - https://github.com/em1208/adrf
- Django ASGI Handler with Lifespan protocol support - https://github.com/illagrenan/django-asgi-lifespan
- OpenAI API Library (Python) - https://github.com/openai/openai-python
- Uvicorn (ASGI Runner) - https://github.com/Kludex/uvicorn
- PyMilvus (Mivlus API Library) - https://github.com/milvus-io/pymilvus
- psycopg (Postgres API Library) - https://github.com/psycopg/psycopg
### Docker Containers
#### Databases
- Milvus (Vector Database) - https://github.com/milvus-io/milvus
- Postgres (User database) - https://github.com/postgres/postgres
#### AI Model Runners
- vLLM - https://github.com/vllm-project/vllm
- llama.cpp - https://github.com/ggml-org/llama.cpp
- Ollama - https://github.com/ollama/ollama
- Docker Model Runner - https://github.com/docker/model-runner
- SGLang - https://github.com/sgl-project/sglang
#### Other
- etcd (Milvus metadata storage) - https://github.com/etcd-io/etcd
- MinIO (persistant storage for large-scale files) - https://github.com/minio/minio

## Licensing
fAIth is released under the GNU General Public License v3.0 (GPLv3). We believe that just as God's Word is a gift freely given to all, the tools used to interact with it should remain free for everyone to use, study, and share.

The GPL ensures that fAIth remains a community resource. By mandating that all modifications remain open source, we guarantee that no one can restrict access to this project. This transparency allows the community to audit the code, ensuring that the software remains safe, authentic, and true to its purpose of helping users grow closer to God.
