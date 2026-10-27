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

## Privacy and Security
fAIth is a Bible study app, and some of its users may live in countries where Christianity is persecuted. There, an account and the study activity connected to it could be used against the person who owns them. We want every account and every piece of data to be protected at all cost. That is why the security and privacy measures below go further than a typical app needs. The same measures make fAIth more resilient against attackers and hostile actors in general, which helps protect our users' safety beyond their accounts.

### Django Defaults
These protections come from Django itself and are on without any fAIth configuration. The [Django security documentation](https://docs.djangoproject.com/en/6.0/topics/security/) describes the threats they address.
- **Password hashing:** Passwords are never stored in plain text. Django's first password hasher is PBKDF2-SHA256, so new passwords are hashed with it before saving.
- **Session invalidation on password change:** Changing a user's password logs out all of their sessions.
- **Clickjacking protection:** `X_FRAME_OPTIONS` defaults to `DENY`, which sends `X-Frame-Options: DENY` through `XFrameOptionsMiddleware`, so other sites can't embed pages in a frame.
- **MIME sniffing protection:** `SECURE_CONTENT_TYPE_NOSNIFF` defaults to `True`, which sends `X-Content-Type-Options: nosniff` through `SecurityMiddleware`, so browsers don't reinterpret files as a different type.
- **Referrer policy:** `SECURE_REFERRER_POLICY` defaults to `same-origin`, so other sites don't receive full page URLs in the `Referer` header.
- **Cross-origin isolation:** `SECURE_CROSS_ORIGIN_OPENER_POLICY` defaults to `same-origin`, which stops other sites from holding a live reference to fAIth's window.
- **Session cookies:** `SESSION_COOKIE_HTTPONLY` defaults to `True`, which hides the cookie from JavaScript. `SESSION_COOKIE_SAMESITE` defaults to `Lax`, which stops the cookie being sent on most cross-site requests. `SESSION_COOKIE_AGE` defaults to two weeks.
- **Server-side sessions:** `SESSION_ENGINE` defaults to the database backend, so session data is stored on the server and the browser only holds a session ID.
- **Template escaping:** Template autoescaping defaults to `True`, which blocks most cross-site scripting (XSS).
- **Database queries:** Django's ORM passes query values as parameters, which protects against SQL injection.

### Account Passwords
- New passwords must pass the project's password validators: they can't be too similar to the username, must meet a minimum length, can't be a common password, and can't be all numeric.
- Changing a password requires the current password and must be different from the old one. The user's current session stays signed in, so only their other sessions are signed out.

### Two-Factor Authentication (Authenticator Apps)
- Users can add an authenticator app (TOTP) at signup or later in their profile. Once enabled, login asks for a 6-digit code after the password.
- TOTP secrets are encrypted before they are stored, using Fernet (AES-128-CBC with HMAC-SHA256) and a dedicated `TOTP_ENCRYPTION_KEY`.
- The QR code is drawn on the server as inline SVG, so the secret is never sent to a third-party service.
- Authenticator secrets are generated from the operating system's secure random source (`os.urandom`).

### Recovery Codes
- Each account gets 10 recovery codes. Each code is 128 random bits from Python's `secrets` module.
- Codes are shown once and never stored in plain text. Only PBKDF2-SHA256 hashes are kept (100,000 iterations, salted per device).
- Each code works once. It is deleted on use in a single database query, so two requests can't both spend it.
- During signup and recovery, the codes waiting in the session are encrypted with a separate `RECOVERY_CODE_ENCRYPTION_KEY`.
- The pages that show recovery codes are never cached by browsers or proxies.

### Brute-Force Protection and Lockouts
- Failed logins and recovery attempts are counted per client with django-axes. After 5 failures, the client is locked out for 15 minutes.
- Counting is per client, not per account. One client can't spread guesses across many accounts without being locked out.
- A successful login does not reset the failure count, so a user can't clear their own failures and keep guessing on another account.
- The authenticator app's built-in throttle is turned off. That throttle is shared by everyone, so anyone who knows a user's password could lock them out of their authenticator. Wrong codes still count toward the per-client lockout instead.
- Every failed login returns the same message, whether the username, password, or authenticator code was wrong or missing. The message doesn't reveal whether an account exists or whether it has an authenticator app.
- Recovery responses don't reveal whether a username exists. The lockout message doesn't say whose account is locked or how many attempts were counted.

### Privacy and Data Minimisation
- **Client identifiers are hashed before storage.** IP addresses and usernames are stored only as HMAC-SHA256 hashes keyed with `DJANGO_SECRET_KEY`, so they can't be recovered without that key. Usernames are normalised to lowercase before hashing, and the plain username is masked in stored request data. This follows GDPR's data-minimisation principle.
- **Failed-attempt records are short-lived.** Each record includes the client's user agent and requested path, and is removed once its 15-minute lockout window has passed, during cleanup on a later failed login.
- **Successful logins are not logged.** django-axes' access log, which would store the IP and user agent for every login, is disabled.
- **Account IDs are random UUIDv4 values.** They aren't sequential, so an ID doesn't reveal when an account was created or how many accounts exist, and they are hard to guess (122 random bits). This still holds if IDs end up in logs, error reports, or other places outside the database. Access to each account is enforced on the server, so the IDs are never the only protection.
- **Proxy headers are only trusted when configured.** `X-Forwarded-For` is read only when `DJANGO_TRUSTED_PROXY_COUNT` matches the deployment. Otherwise a client could spoof its address to evade lockouts.
- **No third-party scripts or CDN assets.** The templates don't load external JavaScript or CSS.
- **Web searches go through a self-hosted SearXNG instance** that is not reachable from outside the Docker network.
- **Only the web app's port is published to the host.** The database, vector database, and model services are not exposed outside Docker.
- **Account deletion** requires the password (and an authenticator code, if enabled), then removes the user and their linked authentication devices and recovery codes.

### Encryption and Secrets
- Authenticator secrets are encrypted at rest with Fernet, and recovery codes in the session are encrypted with a second Fernet key. The two keys are separate, so one can be rotated without breaking the other.
- The app refuses to start if `DJANGO_SECRET_KEY`, `RECOVERY_CODE_ENCRYPTION_KEY`, or `TOTP_ENCRYPTION_KEY` is missing, left at the template default, or not a valid key.
- The `.env` file is ignored by git, so secrets are not committed. `.env_template` contains only placeholders.

### Dependencies
- Every Python dependency is pinned to an exact version in `requirements.txt`, so each install uses the same libraries and an update can't change them unnoticed.

### Web Application Protections
- **CSRF protection:** Every form POST, including login, signup, recovery, profile changes, logout, and AI requests, requires Django's CSRF token. Tests check that a POST without a valid token is refused.
- **Safe redirects:** The `next` parameter after login or logout is only followed when it's a local path on the same host, so attackers can't use fAIth to redirect users to other sites.
- **Sensitive pages are never cached:** Signup, recovery, and profile pages that show codes or account data use `never_cache`.
- **Host header validation:** Only hosts listed in `DJANGO_ALLOWED_HOSTS` are accepted.
- **HTTPS mode (`DJANGO_HTTPS`):** When turned on, cookies are sent only over HTTPS, HTTP is redirected to HTTPS, and HSTS is enabled. It is off by default so local HTTP testing still works.
- **Signup races:** Signup takes a database lock on the username, so two requests can't create accounts whose names differ only by letter case.

### Offline Operation
- Once setup is complete, the app is designed to run without internet access and to be reached over a local network. Authentication, two-factor checks, recovery codes, sessions, and lockouts are all handled by the app and its local Postgres database, with no outside service involved. Setup itself needs internet access to pull Docker images, download language models from Hugging Face (`HF_TOKEN`), and download WordNet data (`WORDNET_DOWNLOAD_VERSION`).
- Not available offline: web, image, and map search through SearXNG, and any external LLM or embedding endpoint set in `BASE_LLM_URL` or `BASE_EMBEDDING_URL`.
- User data is stored in the local Postgres database: account details, authenticator devices, recovery codes, sessions, and lockout records.
- When a local model runner is configured (llama.cpp, vLLM, Ollama, or SGLang), the language model and embedding model run in local containers, so study requests stay on the host.
- Front-end libraries (Bootstrap, htmx, Popper, and Bootstrap Icons) ship with the app, so pages don't load scripts or styles from a CDN.

### Testing
- Automated tests run on an in-memory SQLite database, set globally in `fAIth/test_settings.py`, so test data never reaches the Postgres database.
- Automated tests check CSRF enforcement on every POST route, confirm that raw IP addresses never reach the lockout tables, and confirm that the lockout identifier changes with the secret key and the proxy setting.
- The Django CI workflow runs a system check with test keys, so a misconfigured settings file fails the build.

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
- cryptography (Cryptographic recipes and primitives)
   - Python Cryptographic Authority. (2014). cryptography. GitHub. Retrieved October 20, 2026, from https://github.com/pyca/cryptography
- Django
   - Django. (2012). django. GitHub. Retrieved August 30, 2026, from https://github.com/django/django
- Django ASGI Lifespan (Django ASGI Handler with Lifespan protocol support)
   - Dohnal, V. (2022). django-asgi-lifespan. GitHub. Retrieved August 30, 2026, from https://github.com/illagrenan/django-asgi-lifespan
- django-axes (Login attempt rate limiting and lockout)
   - Jazzband. (2008). django-axes. GitHub. Retrieved October 20, 2026, from https://github.com/jazzband/django-axes
- Django Ninja (REST Framework)
   - Kucheryaviy, V. (2020). django-ninja. GitHub. Retrieved August 30, 2026, from https://github.com/vitalik/django-ninja
- django-otp (One-time password (TOTP/HOTP) support)
   - Sagerson, P. (2012). django-otp. GitHub. Retrieved October 20, 2026, from https://github.com/django-otp/django-otp
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
- segno (QR code generator)
   - Heuer, L. (2016). segno. GitHub. Retrieved October 20, 2026, from https://github.com/heuer/segno
- Uvicorn (ASGI Runner) - https://github.com/Kludex/uvicorn
   - Trylesinski, M., & Christie, T. Uvicorn [Computer software]. https://github.com/Kludex/uvicorn
- WhiteNoise (Static file serving)
   - Evans, D. (2013). whitenoise. GitHub. Retrieved August 30, 2026, from https://github.com/evansd/whitenoise

## Licensing
fAIth is released under the GNU General Public License v3.0 (GPLv3). We believe that just as God's Word is a gift freely given to all, the tools used to interact with it should remain free for everyone to use, study, and share.

The GPL ensures that fAIth remains a community resource. By mandating that all modifications remain open source, we guarantee that no one can restrict access to this project. This transparency allows the community to audit the code, ensuring that the software remains safe, authentic, and true to its purpose of helping users grow closer to God.
