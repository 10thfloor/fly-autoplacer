#!/bin/sh
set -eu

case "${1:-placer}" in
  dashboard)
    cd /app/placer-dashboard
    exec gosu app deno serve -A --frozen --cached-only --host 0.0.0.0 --port 8080 ./server.ts
    ;;
  placer)
    cd /app/placer-service
    # Fly mounts a new persistent volume as root. Drop privileges after initialization.
    mkdir -p data
    chown -R app:app data
    exec gosu app python main.py
    ;;
  *)
    echo "Unknown process group: $1" >&2
    exit 1
    ;;
esac
