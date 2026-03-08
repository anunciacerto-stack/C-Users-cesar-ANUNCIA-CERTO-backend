#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env.production ]; then
  cp .env.production.example .env.production
  echo "Arquivo .env.production criado a partir do exemplo. Edite antes de continuar."
  exit 1
fi

docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

docker compose -f docker-compose.prod.yml --env-file .env.production exec -T backend npx prisma migrate deploy

docker compose -f docker-compose.prod.yml --env-file .env.production restart backend nginx

docker compose -f docker-compose.prod.yml --env-file .env.production ps

echo "Deploy finalizado."
