#!/usr/bin/env sh
set -eu

ROOT_DIR="${ROOT_DIR:-/opt/factoryvision}"
COMPOSE_FILE="${COMPOSE_FILE:-deploy/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-deploy/.env.prod}"

cd "$ROOT_DIR"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE. Create it from deploy/.env.prod.example before deploying." >&2
  exit 1
fi

echo "[deploy] commit=$(git rev-parse --short HEAD)"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config >/dev/null
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build frontend backend
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d db backend frontend
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend python manage.py migrate --noinput
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend python manage.py collectstatic --noinput
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
curl -fsS http://127.0.0.1:18080/ >/dev/null
curl -fsS http://127.0.0.1:18080/api/health/ >/dev/null
echo "[deploy] ok"
