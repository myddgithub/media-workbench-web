#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example; verify NAS_MEDIA_PATH/PUID/PGID before retrying." >&2
  exit 2
fi

mkdir -p state
docker compose config --quiet
docker compose up -d --build
docker compose ps
