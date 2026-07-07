# Fitness AI Agent

Local-first FastAPI fitness agent with PostgreSQL, Redis, Qdrant, Ollama,
WhatsApp webhook scaffolding, email summaries, and deployment-ready Docker
Compose support.

## Local Startup

1. Copy `.env.example` values into your local environment file.
2. Start the core stack:

```bash
docker compose up -d --build
```

3. Run database migrations:

```bash
docker compose exec backend alembic upgrade head
```

4. Check health:

```bash
curl http://localhost:8000/api/v1/health
```

The API is available at `http://localhost:8000`.

## Optional Ollama Container

The default config expects Ollama on the host at
`http://host.docker.internal:11434`. To run Ollama through Compose instead:

```bash
docker compose --profile local-llm up -d ollama
```

Then set:

```env
OLLAMA_BASE_URL=http://ollama:11434
```

Pull the models you need inside the Ollama container or against your host
Ollama runtime.

## Cloudflare Tunnel

Cloudflare Tunnel is part of the default Compose stack. Keep the tunnel token
out of Git in the ignored root `.env` file:

```env
CLOUDFLARE_TUNNEL_TOKEN=<cloudflare-tunnel-token>
```

Before public exposure, use:

```env
DEBUG=false
DOCS_ENABLED=false
API_KEY_ENABLED=true
API_KEY=<strong-random-api-key>
WHATSAPP_PROVIDER=meta
WHATSAPP_META_VERIFY_TOKEN=<meta-webhook-verify-token>
```

Then start the stack:

```bash
docker compose up -d --build
```

The tunnel should point to the backend service at `http://backend:8000` in the
Cloudflare dashboard. Use this Meta callback URL:

```text
https://<your-cloudflare-hostname>/api/v1/webhooks/whatsapp
```

When `API_KEY_ENABLED=true`, only the WhatsApp webhook path is public. All other
routes require `X-API-Key`.

## Backups

Create a PostgreSQL backup:

```bash
scripts/backup_postgres.sh
```

Restore from a backup:

```bash
scripts/restore_postgres.sh backups/fitness_ai_agent_YYYYMMDDTHHMMSSZ.sql
```

Backups are written to `backups/`, which is ignored by Git.

## Tests and Checks

Install dev dependencies in the backend environment:

```bash
pip install -r backend/requirements-dev.txt
```

Run tests:

```bash
cd backend
pytest
```

Run lint and format checks:

```bash
ruff check backend
ruff format --check backend
```

## Deployment Notes

- Keep `.env` and tunnel/API/SMTP tokens out of Git.
- Use persistent Docker volumes for Postgres, Redis, Qdrant, and Ollama.
- Run `alembic upgrade head` after deploys.
- Use `/api/v1/health` and service-specific health endpoints for monitoring.
