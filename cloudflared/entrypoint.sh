#!/bin/sh
set -e
TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-${TUNNEL_TOKEN:-}}"
if [ -n "$TOKEN" ]; then
  exec cloudflared tunnel --no-autoupdate --protocol http2 run --token "$TOKEN"
fi
echo "Sin CLOUDFLARE_TUNNEL_TOKEN: túnel rápido. La URL cambia cada vez que este contenedor arranca."
exec cloudflared tunnel --no-autoupdate --protocol http2 --url http://app:8000
