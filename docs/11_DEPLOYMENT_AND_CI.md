# Phase 15 and 16

## Phase 15: Deployment Prep

The Compose stack now includes persistent services for:

- `db`
- `redis`
- `qdrant`
- `backend`
- optional `ollama` with the `local-llm` profile
- optional `cloudflared` with the `tunnel` profile

Persistent volumes:

- `postgres_data`
- `redis_data`
- `qdrant_data`
- `ollama_data`

Cloudflare Tunnel uses `CLOUDFLARE_TUNNEL_TOKEN` at runtime. Do not commit the
actual token. Start it with:

```bash
export CLOUDFLARE_TUNNEL_TOKEN="your-token"
docker compose --profile tunnel up -d cloudflared
```

PostgreSQL backup scripts:

- `scripts/backup_postgres.sh`
- `scripts/restore_postgres.sh`

## Phase 16: Testing and CI

Added:

- `backend/pytest.ini`
- `backend/requirements-dev.txt`
- `backend/tests/`
- `.github/workflows/backend.yml`
- `pyproject.toml` Ruff config

Local checks:

```bash
pip install -r backend/requirements-dev.txt
cd backend
pytest
cd ..
ruff check backend
ruff format --check backend
```
