### Stage 1: Builder ###
FROM python:3.13-slim AS builder

# Create the app directory
RUN mkdir /app

# Set the working directory
WORKDIR /app

# Set environment variables to optimize Python
# Prevents Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Upgrade pip
RUN pip install --upgrade pip

# Copy the requirements file first (better caching)
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt



### Stage 2: Production ###
FROM python:3.13-slim

# Create non-root user
RUN useradd -m -r appuser && mkdir /app && chown -R appuser /app

# Copy the Python dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Set the working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Set environment variables to optimize Python
# Prevents Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Expose the application port
EXPOSE 8000

RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Start uvicorn
CMD ["sh", "-c", "python scripts/docker_milvus_initializer.py && python manage.py migrate && python manage.py collectstatic --noinput --clear && uvicorn fAIth.asgi:application --host 0.0.0.0 --port 8000"]