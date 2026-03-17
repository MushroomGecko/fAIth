---
name: Application Host Bug Report
about: Report issues with setting up, deploying, or running fAIth (Docker, Milvus, Postgres, LLMs, etc.)
title: "[SETUP] Brief description of the issue"
labels: 'setup'
assignees: ''

---

## **What component is failing?**
Which part of the fAIth setup is having issues?

- [ ] Docker / Docker Compose setup
- [ ] Postgres database
- [ ] Milvus vector database (or etcd/SeaweedFS)
- [ ] Embedding service (local or third-party)
- [ ] LLM service (local or third-party)
- [ ] Django/Uvicorn application startup
- [ ] GPU/CUDA/Hardware configuration
- [ ] Network/connectivity
- [ ] API authentication (API keys, credentials)
- [ ] Other: [describe]

---

## **What's happening?**
Describe the error or unexpected behavior you're encountering.

*Example: "Docker Compose fails to start the Milvus container with an error about port 19530 being in use."*

---

## **Steps to reproduce**
What did you do when the problem occurred? Be specific about your setup:

1. [e.g., "Ran `python ./scripts/build_docker_compose.py` with default settings"]
2. [e.g., "Executed `docker compose up -d`"]
3. [e.g., "Waited 2 minutes, then checked logs"]
4. [What happened - e.g., "Milvus container exited with status 1"]

---

## **Error messages and logs**
Please provide the exact error messages. For Docker issues, run:
```bash
docker compose logs -f [service-name]
```

Or for Python/application errors:
```bash
docker compose logs -f webapp
```

Copy the **complete error message** and the last 20-30 lines of logs:

```
[Paste error output here]
```

---

## **Your setup**
*This helps us understand your environment and hardware limitations.*

- **Operating System:** [e.g., Ubuntu 24.04, Fedora 42, Windows 11 WSL2]
- **Docker version:** [run: `docker --version`]
- **Docker Compose version:** [run: `docker compose version`]
- **Available RAM:** [e.g., 16GB, 8GB]
- **Available VRAM:** [e.g., NVIDIA RTX 4080 with 12GB, CPU-only]
- **GPU Support:** [ ] NVIDIA (with CUDA) [ ] AMD (with ROCm) [ ] Intel (with Vulcan) [ ] CPU-only
- **Python version:** [run: `python --version`]
- **Model/Service Setup:**
  - [ ] **Local models** (running in Docker)
  - [ ] **Third-party providers** (OpenAI, Anthropic, HuggingFace, etc.)

**If using LOCAL models:**
  - `EMBEDDING_MODEL_ID`: [default: `Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0`]
  - `LLM_MODEL_ID`: [default: `unsloth/Qwen3.5-4B-GGUF:Q4_K_M`]
  - `EMBEDDING_MODEL_RUNNER`: [`vllm`, `llama_cpp`, `ollama`, or `sglang`]
  - `LLM_MODEL_RUNNER`: [`vllm`, `llama_cpp`, `ollama`, or `sglang`]
  - `EMBEDDING_GPU_TYPE`: [`nvidia`, `amd`, `intel`, or `cpu`]
  - `LLM_GPU_TYPE`: [`nvidia`, `amd`, `intel`, or `cpu`]
  - `EMBEDDING_DRIVER`: [`cuda`, `rocm`, `vulkan`, or `cpu`] (Intel uses `vulkan`)
  - `LLM_DRIVER`: [`cuda`, `rocm`, `vulkan`, or `cpu`] (Intel uses `vulkan`)

**If using THIRD-PARTY providers:**
  - `BASE_EMBEDDING_URL`: [e.g., `https://openrouter.ai/api/v1`]
  - `BASE_LLM_URL`: [e.g., `https://openrouter.ai/api/v1`]
  - Which provider(s)? [e.g., OpenAI, Anthropic, HuggingFace, Azure, other: ___]
  - Are API keys configured? [ ] Yes [ ] No [ ] Not sure
  - **NOTE: Do NOT share your API keys or credentials in this issue. Keep all sensitive information private.**

---

## **What you've already tried**
Have you attempted any troubleshooting? (Check all that apply)

- [ ] Restarted Docker daemon: `sudo systemctl restart docker`
- [ ] Cleaned up Docker: `docker compose down && docker system prune`
- [ ] Removed old volumes (helps with SeaweedFS errors): `docker compose down -v && sudo rm -rf ./volumes`
- [ ] Checked available disk space: `df -h`
- [ ] Verified `.env` file is copied from `.env_template`
- [ ] Checked system resource limits (RAM, VRAM)
- [ ] Reviewed README.md setup instructions
- [ ] Other: [describe]

---

## **Additional context**
Any other information that might help us debug:
- Did this work before, or is this a fresh setup?
- Are you using custom/non-default models?
- Is this a multi-machine setup (e.g., different hosts for app vs. database)?
- Any network or firewall restrictions?

*Optional - only add if relevant.*
