#!/bin/sh

set -euo

log() {
    printf '[ENTRYPOINT] %s
' "$1"
}

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
exec su faith_user -c "uvicorn fAIth.asgi:application --host 0.0.0.0 --port 8000 --workers 1"