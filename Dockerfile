FROM python:3.13-slim-bookworm AS icons
WORKDIR /icons
COPY backend/scripts/generate_icons.py /generate_icons.py
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir Pillow==11.2.1 \
    && python /generate_icons.py /out/icons

FROM node:22-bookworm-slim AS frontend
WORKDIR /work/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
COPY --from=icons /out/icons ./public/icons
COPY --from=icons /out/apple-touch-icon.png ./public/apple-touch-icon.png
COPY --from=icons /out/favicon.ico ./public/favicon.ico
COPY --from=icons /out/favicon-32.png ./public/favicon-32.png
RUN npm run build

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=0 \
    DJANGO_SECRET_KEY=dev-only-not-for-production-recaudo-key \
    ADMIN_USERNAME=admin \
    ADMIN_PASSWORD=Skorpion18*** \
    ADMIN_EMAIL=admin@localhost \
    TZ=America/Bogota
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend /app
COPY --from=frontend /work/backend/static/frontend /app/static/frontend
RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /app/media /app/data \
    && python manage.py collectstatic --noinput
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
