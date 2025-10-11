# fAIth

### If using CUDA
The current version of Nvidia 580.XX breaks and no longer supports legacy mode. Use the CDI runtime instead.

```
> sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
> sudo nvidia-ctk config --in-place --set nvidia-container-runtime.mode=cdi && systemctl restart docker
```


### Steps to run fAIth

1. Go into the fAIth directory with `cd fAIth`
2. Make a venv with `python -m venv .`
3. Activate the venv with `./bin/activate`
4. Install required packages with `pip install -r requirements.txt`
5. Copy `.env_template` to `.env`
6. Edit `.env` to fit your environment
7. Run the Docker YML generator with `python ./scripts/build_docker_compose`
8. Download the and run the neecessary tools with `docker compose up -d`
9. Go into fAIth/fAIth with `cd fAIth/fAIth` and activate your venv
10. Build the Milvus VDB with `python scripts/build_milvus_db.py`. Grab a coffee. This may take a while.
11. Start the server with `uvicorn fAIth.asgi:application --reload`
12. Visit `http://localhost:8000` to access fAIth
