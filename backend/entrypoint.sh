#!/bin/sh
set -e

# Railway Free/Hobby: Volume en /data → SQLite + media persistentes.
# Sin Volume la BD se recrea y el seed vuelve a cargar admin + catálogo.
mkdir -p /app/data /app/media
if [ -n "${RAILWAY_VOLUME_MOUNT_PATH:-}" ]; then
  mkdir -p "${RAILWAY_VOLUME_MOUNT_PATH}" "${RAILWAY_VOLUME_MOUNT_PATH}/media"
fi
if [ -n "${SQLITE_PATH:-}" ]; then
  mkdir -p "$(dirname "$SQLITE_PATH")"
fi
if [ -n "${MEDIA_ROOT:-}" ]; then
  mkdir -p "$MEDIA_ROOT"
fi

# Migraciones + seed (admin Carlos*2021*, padrinos/familias). No hace falta generar claves ni DNS.
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
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT}" --workers ${GUNICORN_WORKERS:-1} --threads 1 --timeout 90
