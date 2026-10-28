#!/bin/sh
set -e
mkdir -p /app/data /app/media
if [ -n "${RAILWAY_VOLUME_MOUNT_PATH:-}" ]; then
  mkdir -p "${RAILWAY_VOLUME_MOUNT_PATH}/media"
fi
if [ -n "${SQLITE_PATH:-}" ]; then
  mkdir -p "$(dirname "$SQLITE_PATH")"
fi
if [ -n "${MEDIA_ROOT:-}" ]; then
  mkdir -p "$MEDIA_ROOT"
fi

if [ -f /app/data/restore.json ] && [ ! -f /app/data/.restored ]; then
  SKIP_SEED=1 python manage.py migrate --noinput
  python manage.py loaddata /app/data/restore.json
  mv /app/data/restore.json /app/data/restore.json.done
  touch /app/data/.restored
else
  python manage.py migrate --noinput
  python manage.py seed_admin
fi

python manage.py collectstatic --noinput
PORT="${PORT:-8000}"
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT}" --workers ${GUNICORN_WORKERS:-2} --threads 1 --timeout 90
