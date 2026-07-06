# MVP Stabilization Audit

Last updated: 2026-07-06

This audit follows the MVP stabilization plan in
`fitness_ai_agent_mvp_stabilization_codex.md`. No new product features were
added.

## Summary

The local MVP is stable enough to continue toward controlled inbound exposure
and real WhatsApp integration.

The audit found and fixed one configuration robustness issue:

- Host environments with `DEBUG=release` caused settings validation to fail
  before tests could collect. `backend/app/core/config.py` now normalizes
  `release`, `prod`, and `production` to `False`, and `debug`, `dev`, and
  `development` to `True`.

Everything else required for local stabilization passed:

- Docker Compose build/start succeeded.
- Core containers are running.
- Alembic migrations are at head.
- Alembic autogenerate check reports no new upgrade operations.
- Pytest passes.
- Ruff check passes.
- Ruff format check passes.
- Required local endpoints pass.
- Agent core text flows pass.
- Mock WhatsApp webhook delegates to the agent.
- Ollama is reachable and `qwen3-vl:8b` is available.
- `backend/.env` is ignored by Git.

## Commands Run

Docker and service verification:

```bash
docker info
docker compose up -d --build
docker compose ps
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ai/models/health
ollama list
```

Migration verification:

```bash
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend alembic current
docker compose exec -T backend alembic check
```

Test and lint verification:

```bash
docker compose exec -T backend python -m pip install --user -r requirements-dev.txt
docker compose exec -T backend python -m pytest -q
docker compose exec -T backend python -m ruff check .
docker compose exec -T backend python -m ruff format --check .
```

Host-side Ruff was also run against the repo-level config:

```bash
/tmp/fitness-mvp-audit-venv/bin/python -m ruff check backend
/tmp/fitness-mvp-audit-venv/bin/python -m ruff format --check backend
```

Secrets and ignore checks:

```bash
git check-ignore -v backend/.env .env .env.example backend/.env.example
rg -n "(eyJ|CLOUDFLARE_TUNNEL_TOKEN|WHATSAPP_META_ACCESS_TOKEN|SMTP_PASSWORD|API_KEY=|Bearer |sk-[A-Za-z0-9])" .
```

## Docker Status

`docker compose up -d --build` succeeded.

Running containers:

```text
fitness_ai_backend   Up, healthy
fitness_ai_db        Up, healthy
fitness_ai_redis     Up, healthy
fitness_ai_qdrant    Up
```

Notes:

- Qdrant does not currently expose a Compose healthcheck, so `docker compose ps`
  shows it as `Up`, not `healthy`.
- The application health endpoint confirmed Qdrant connectivity as `ok`.
- Cloudflare Tunnel was not started during this audit, which matches the
  stabilization plan: local verification comes first.

## Migration Status

Alembic status:

```text
current: 20260706_0005 (head)
check: No new upgrade operations detected.
```

Result: passed.

## Test and Lint Status

Container pytest:

```text
10 passed
```

Warnings:

- FastAPI `on_event` deprecation warnings.
- Starlette/FastAPI TestClient warning about `httpx`.

Container Ruff:

```text
ruff check .: passed
ruff format --check .: passed
```

Host Ruff with repo-level `pyproject.toml`:

```text
ruff check backend: passed
ruff format --check backend: passed
```

## Endpoint Smoke Tests

Status code checks:

```text
/                              200
/docs                          200
/api/v1/status                 200
/api/v1/health                 200
/api/v1/health/db              200
/api/v1/health/redis           200
/api/v1/health/qdrant          200
/api/v1/health/ollama          200
```

Aggregate health:

```text
app: ok
db: ok
redis: ok
qdrant: ok
ollama: ok
```

Ollama model health:

```text
status: ok
server_reachable: true
model: qwen3-vl:8b
model_available: true
```

Required models present locally:

```text
qwen3-vl:8b
nomic-embed-text:latest
```

## Agent Smoke Tests

A throwaway user was created for the audit.

Passed agent requests:

- Meal text:
  - Request: `I ate 2 eggs, 1 paratha and 1 cup chai`
  - Result: `completed`, `meal_text`, meal persisted.
- Workout:
  - Request: `Bench press 50kg 3 sets of 10`
  - Result: `completed`, `workout_log`, workout persisted.
- Body weight:
  - Request: `My weight today is 84.5 kg`
  - Result: `completed`, `weight_log`, body-weight log persisted.
- Summary:
  - Request: `How am I doing today?`
  - Result: `completed`, `summary_request`, daily summary generated.

Result: passed.

## WhatsApp Mock Smoke Test

Local webhook request:

```json
{
  "from": "+15551234567",
  "user_id": 4,
  "type": "text",
  "text": "I ate chicken rice"
}
```

Result:

```text
status: received
provider: mock
intent: meal_text
meal_id: populated
error: null
```

The webhook parsed the payload, delegated to the final agent, and produced a
mock provider reply.

Result: passed.

## Security and Git Safety

`backend/.env` is ignored:

```text
.gitignore:2:backend/.env backend/.env
```

Secret scan findings:

- Cloudflare token references are environment-variable placeholders.
- WhatsApp/SMTP/API-key mentions in docs are empty examples/placeholders.
- `Bearer` appears in `meta_provider.py` as code constructing an HTTP
  authorization header.
- No real token from the earlier Cloudflare setup was found in tracked files.

Important Git note:

`git status` currently shows the project files as untracked. Before committing,
review the full diff carefully, then commit only after confirming secrets remain
ignored.

## What Was Fixed

### Config Debug Normalization

File:

```text
backend/app/core/config.py
```

Problem:

```text
DEBUG=release
```

from the host environment caused Pydantic settings validation to fail during
test collection.

Fix:

- Added a `debug` field validator.
- Interprets `release`, `prod`, and `production` as `False`.
- Interprets `debug`, `dev`, and `development` as `True`.
- Leaves all other values to Pydantic's normal boolean parsing.

This keeps normal `.env` behavior unchanged while making local tooling less
brittle.

## Remaining Risks

These are not blocking local MVP stabilization, but they should be handled
before real public usage.

1. Real WhatsApp image flow is incomplete.

   Meta image payloads provide media IDs. The backend currently passes
   `image_id` and `image_url` through to the agent, but does not yet download
   media from Meta. Real image messages need a downloader before meal-photo
   analysis can work end to end.

2. Real WhatsApp users are not mapped by phone number yet.

   Local payloads can pass `user_id`. Real WhatsApp webhooks should map
   incoming phone numbers to `users.phone_number`, and return onboarding copy
   when no user is found.

3. API-key auth is disabled locally.

   Before exposing non-webhook routes publicly, set:

   ```env
   API_KEY_ENABLED=true
   API_KEY=<strong-random-value>
   ```

4. Debug/docs exposure should be reviewed before public access.

   For production-style exposure:

   ```env
   DEBUG=false
   ```

   Consider whether `/docs`, `/openapi.json`, and debug endpoints should remain
   publicly reachable.

5. Qdrant image is still `latest`.

   Pin the Qdrant Docker image before treating the deployment as production-like.

6. FastAPI lifespan migration remains.

   The app still uses `@app.on_event`, which works but emits deprecation
   warnings. Replace with lifespan handlers in a cleanup pass.

7. TestClient warning remains.

   FastAPI/Starlette emits a TestClient warning about `httpx`. This is not
   blocking, but should be tracked during dependency upgrades.

## Cloudflare Guidance

Do not enable strict outbound allowlisting yet.

Recommended rollout:

1. Keep stabilizing locally.
2. Use Cloudflare Tunnel for inbound only after local checks pass.
3. Add Cloudflare Gateway DNS/security visibility on the Mac.
4. Confirm Docker/container traffic appears in Gateway logs.
5. Slowly add outbound rules once expected traffic is understood.

Cloudflare Tunnel protects inbound exposure. It does not automatically govern
all server-initiated outbound traffic.

## Recommended Next Engineering Work

After this audit, the next real feature should be:

```text
Real WhatsApp media download and phone-number-to-user mapping.
```

Target behavior:

1. Meta webhook receives a media ID.
2. Backend resolves WhatsApp phone number to `users.phone_number`.
3. If no user exists, backend returns onboarding guidance.
4. Backend downloads media metadata and binary from Meta securely.
5. Backend validates file type and size.
6. Backend stores image through the existing image storage service.
7. Backend passes local image path or base64 into the existing final agent flow.
8. Agent analyzes meal, estimates nutrition, saves meal, stores memory, and
   replies through WhatsApp.

## Audit Result

Result: passed with one fix.

The local MVP is stable for continued local development and controlled inbound
Tunnel testing. Real WhatsApp media download and phone-number user mapping
should be implemented before relying on real WhatsApp photo workflows.
