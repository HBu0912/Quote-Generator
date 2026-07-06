#!/bin/sh
set -e
cd "$(dirname "$0")"
export APP_PASSWORD="${APP_PASSWORD:-TopVN26}"
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8080}"
export FLASK_DEBUG=0
if [ -z "$SECRET_KEY" ]; then
  export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
fi
echo "Starting Quote Generator on http://${HOST}:${PORT}"
echo "Password: (set via APP_PASSWORD env var)"
exec python3 -m gunicorn --bind "${HOST}:${PORT}" --workers 1 --threads 4 --timeout 120 app:app
