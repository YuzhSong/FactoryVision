# FactoryVision production deployment

This deployment runs only the cloud-side services:

- Vue frontend, served by Nginx.
- Django backend, served by Daphne ASGI for HTTP and WebSocket routes.
- PostgreSQL database with a persistent Docker volume.
- Existing SRS on the server is preserved and not managed by this compose file.
- AIService remains on the local GPU workstation and is not built or started in cloud production.

## Files

- `frontend/Dockerfile`: multi-stage Vite build and Nginx static serving.
- `backend/Dockerfile`: Python 3.14 backend runtime.
- `backend/entrypoint.sh`: check, migrate, collectstatic, then start Daphne.
- `deploy/docker-compose.prod.yml`: frontend, backend and PostgreSQL.
- `deploy/nginx/frontend.conf`: Nginx inside the frontend container.
- `deploy/nginx/factoryvision.conf`: optional host Nginx reverse proxy to `127.0.0.1:18080`.
- `deploy/.env.prod.example`: safe placeholder environment template.
- `deploy/scripts/deploy.sh`: repeatable server deployment command.

## Required server environment

Create `/opt/factoryvision/deploy/.env.prod` from `deploy/.env.prod.example`.
Do not commit the real file.

Generate secrets on the server:

```bash
python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(64))
PY
openssl rand -base64 32
```

## Deploy

```bash
cd /opt/factoryvision
git fetch origin --prune
git checkout dev
git pull --ff-only origin dev
sh deploy/scripts/deploy.sh
```

The compose stack exposes only `127.0.0.1:18080` on the host. Use host Nginx to expose the app publicly and avoid conflicts with the existing SRS ports.

## Health checks

```bash
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml ps
curl -fsS http://127.0.0.1:18080/
curl -fsS http://127.0.0.1:18080/api/health/
```

## Database backup and restore

Backup:

```bash
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml exec -T db \
  pg_dump -U "$DB_USER" "$DB_NAME" > "backup-$(date +%Y%m%d-%H%M%S).sql"
```

Restore only after explicit confirmation:

```bash
cat backup.sql | docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml exec -T db \
  psql -U "$DB_USER" "$DB_NAME"
```

Never run `docker compose down -v` in production unless data deletion is intentional.

## Local AIService to cloud backend

Cloud production cannot reach `http://127.0.0.1:9000` on the local GPU workstation.
Set the local AIService environment instead:

```env
BACKEND_API_BASE_URL=https://webrtc.rainycode.cn/api
STREAM_INPUT_URL=rtmp://81.70.90.222:1935/live/1
STREAM_OUTPUT_URL=rtmp://81.70.90.222:1935/live/1_detected
STREAM_PLAY_URL=https://webrtc.rainycode.cn:8443/live/1_detected.flv
AI_SERVICE_API_TOKEN=<same token as cloud backend>
```

Current frontend fallback calls `/ai-service` only when direct AIService fallback is used. In cloud production this path is intentionally not proxied by default; the preferred flow is local AIService actively pulling config and reporting events to the cloud backend.

## Rollback

```bash
cd /opt/factoryvision
git log --oneline -5
git checkout <previous-good-commit>
sh deploy/scripts/deploy.sh
```

If the new containers fail health checks, keep the previous images and inspect:

```bash
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml logs --tail=200 backend frontend
```
