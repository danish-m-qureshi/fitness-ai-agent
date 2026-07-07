# Implemented Phases Summary

Last updated: 2026-07-06

This document summarizes the phases implemented so far for the local-first
Fitness AI Agent. The project is now implemented through Phase 17.

## Current System Snapshot

The repository now contains a Dockerized FastAPI backend with PostgreSQL,
Redis, Qdrant, Ollama integration, local vision analysis, nutrition estimation,
workout tracking, body-weight logging, daily summaries, WhatsApp webhook
handling, email-summary support, deployment utilities, tests, CI, and the final
agent orchestration layer.

Primary local API:

```text
http://localhost:8000
```

Primary API prefix:

```text
/api/v1
```

Main services in Docker Compose:

- `backend`: FastAPI application.
- `db`: PostgreSQL 16.
- `redis`: Redis 7 with append-only persistence.
- `qdrant`: local vector database for long-term memory.
- `ollama`: optional Compose profile for local LLM runtime.
- `cloudflared`: optional Compose profile for Cloudflare Tunnel.

The default local LLM setup keeps Ollama running on macOS and lets the backend
call it through:

```text
http://host.docker.internal:11434
```

Configured local models:

- Vision model: `qwen3-vl:8b`
- Embedding model: `nomic-embed-text`

## Phase Status Table

| Phase | Status | Summary |
| --- | --- | --- |
| Phase 1 | Implemented | Initial project/backend scaffold and Dockerized local app foundation. |
| Phase 2 | Implemented | FastAPI backend architecture, versioned routes, config, services, schemas, logging, and exception handling. |
| Phase 3 | Implemented | PostgreSQL, SQLAlchemy models, Alembic migrations, and initial persistent domain tables. |
| Phase 4 | Implemented | DB-backed CRUD/service layer for core fitness resources. |
| Phase 5 | Implemented | Local Ollama vision-model integration using `qwen3-vl:8b`. |
| Phase 6 | Implemented | Nutrition catalog, meal macros, food-item estimates, and nutrition APIs. |
| Phase 7 | Implemented | Long-term memory with Ollama embeddings and Qdrant. |
| Phase 8 | Implemented | Meal image upload, local vision analysis, nutrition estimation, and analyzed meal persistence. |
| Phase 9 | Implemented | Normalized workout sessions, exercises, sets, exercise catalog, and progress calculations. |
| Phase 10 | Implemented | WhatsApp webhook, parser, provider abstraction, mock provider, and initial intent handling. |
| Phase 11 | Implemented | Daily summaries, email summary service, and optional scheduled summary jobs. |
| Phase 12 | Implemented | User profile fields and API-key authentication middleware. |
| Phase 13 | Implemented | Production hardening, pinned backend dependencies, non-root Docker image, standardized error envelope. |
| Phase 14 | Implemented | Observability, request IDs, service health checks, debug endpoints, and structured logs. |
| Phase 15 | Implemented | Deployment prep, persistent Compose services, Cloudflare Tunnel profile, and backup/restore scripts. |
| Phase 16 | Implemented | Test suite, Ruff config, dev dependencies, and GitHub Actions workflow. |
| Phase 17 | Implemented | Final fitness agent orchestration layer and unified API/WhatsApp flow. |

## Phase 1: Project Foundation

Phase 1 established the basic local development foundation for the project.

Implemented pieces:

- Project root at `fitness-ai-agent/`.
- Dockerized backend directory under `backend/`.
- Initial FastAPI application entrypoint.
- Local Docker Compose setup for the backend.
- Basic environment file support.
- Local development workflow around Uvicorn and hot reload.

Important files:

- `backend/app/main.py`
- `backend/Dockerfile`
- `docker-compose.yml`
- `backend/.env`

## Phase 2: Backend Architecture

Phase 2 upgraded the backend into a cleaner FastAPI architecture.

Implemented pieces:

- FastAPI app factory via `create_app()`.
- Central API router under `backend/app/api/router.py`.
- Versioned API prefix from settings: `/api/v1`.
- Environment-driven config with `pydantic-settings`.
- Structured logging setup.
- Custom application exceptions.
- Global exception handlers.
- Request/response schemas.
- Service layer pattern.
- Dependency module under `backend/app/api/deps.py`.
- Health, status, and initial meal text endpoints.

Important files:

- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/logging.py`
- `backend/app/core/exceptions.py`
- `backend/app/core/exception_handlers.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/health.py`
- `backend/app/api/routes/status.py`
- `backend/app/api/routes/meals.py`
- `backend/app/schemas/meal.py`
- `backend/app/services/meal_service.py`

Representative endpoints:

- `GET /`
- `GET /api/v1/status`
- `GET /api/v1/health`
- `POST /api/v1/meals/text`

## Phase 3: Database and Initial Persistent Models

Phase 3 added persistent storage with PostgreSQL, SQLAlchemy, and Alembic.

Implemented pieces:

- PostgreSQL service in Docker Compose.
- SQLAlchemy session management.
- Declarative model base.
- Alembic configuration and migration environment.
- Initial migration for core domain tables.
- Initial models for users, meals, workouts, goals, body-weight logs, and daily summaries.

Important files:

- `backend/app/db/base.py`
- `backend/app/db/session.py`
- `backend/app/models/user.py`
- `backend/app/models/meal.py`
- `backend/app/models/workout.py`
- `backend/app/models/goal.py`
- `backend/app/models/body_weight_log.py`
- `backend/app/models/daily_summary.py`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/20260705_0001_phase_3_initial_tables.py`

Tables introduced:

- `users`
- `meals`
- `workouts`
- `goals`
- `body_weight_logs`
- `daily_summaries`

## Phase 4: Core CRUD APIs and Services

Phase 4 made the initial persistent resources usable through services and REST
routes.

Implemented pieces:

- DB-backed CRUD services for core resources.
- API routes for users, meals, goals, daily summaries, and body-weight logs.
- Shared user-existence validation helper.
- Pydantic schemas for create/update/response payloads.
- Standard resource-not-found and conflict behavior.

Important files:

- `backend/app/services/user_service.py`
- `backend/app/services/meal_service.py`
- `backend/app/services/goal_service.py`
- `backend/app/services/body_weight_log_service.py`
- `backend/app/services/daily_summary_service.py`
- `backend/app/services/user_helpers.py`
- `backend/app/api/routes/users.py`
- `backend/app/api/routes/meals.py`
- `backend/app/api/routes/goals.py`
- `backend/app/api/routes/body_weight_logs.py`
- `backend/app/api/routes/daily_summaries.py`

Representative endpoints:

- `POST /api/v1/users`
- `GET /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`
- `POST /api/v1/meals`
- `GET /api/v1/meals`
- `GET /api/v1/meals/{meal_id}`
- `PATCH /api/v1/meals/{meal_id}`
- `DELETE /api/v1/meals/{meal_id}`
- `POST /api/v1/goals`
- `POST /api/v1/body-weight-logs`
- `POST /api/v1/daily-summaries`

## Phase 5: Local LLM and Vision Client

Phase 5 added the local LLM/vision integration layer.

Implemented pieces:

- LLM provider settings in the central config.
- Ollama base URL setting.
- Vision model setting with `qwen3-vl:8b` as the default.
- Abstract vision LLM client interface.
- Ollama vision client implementation.
- Model health endpoint.
- Local-first architecture where the Dockerized backend calls host Ollama.

Important files:

- `backend/app/services/llm/base.py`
- `backend/app/services/llm/ollama_client.py`
- `backend/app/api/routes/ai.py`
- `backend/app/schemas/ai.py`
- `backend/app/core/config.py`

Relevant environment variables:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
VISION_MODEL=qwen3-vl:8b
OLLAMA_TIMEOUT_SECONDS=60
```

Representative endpoint:

- `GET /api/v1/ai/models/health`

## Phase 6: Nutrition Catalog and Nutrition Estimation

Phase 6 added nutrition data modeling and deterministic nutrition estimation.

Implemented pieces:

- `nutrition_foods` table for local nutrition catalog entries.
- `meal_food_items` table for itemized meal estimates.
- Macro fields on meals:
  - calories
  - protein
  - carbs
  - fat
  - nutrition confidence
- Seed data for common foods such as eggs, paratha, chai, rice, chicken breast, chicken biryani, raita, banana, apple, and milk.
- Nutrition estimation service that matches detected foods to local catalog entries.
- Nutrition routes for catalog CRUD, estimating nutrition, applying nutrition to meals, and reading meal nutrition.

Important files:

- `backend/app/models/nutrition_food.py`
- `backend/app/models/meal_food_item.py`
- `backend/app/services/nutrition_service.py`
- `backend/app/api/routes/nutrition.py`
- `backend/app/schemas/nutrition.py`
- `backend/alembic/versions/20260705_0002_phase_6_nutrition.py`

Representative endpoints:

- `POST /api/v1/nutrition/estimate`
- `POST /api/v1/nutrition/foods`
- `GET /api/v1/nutrition/foods`
- `GET /api/v1/nutrition/foods/{food_id}`
- `PATCH /api/v1/nutrition/foods/{food_id}`
- `DELETE /api/v1/nutrition/foods/{food_id}`
- `POST /api/v1/nutrition/meals/{meal_id}/apply`
- `GET /api/v1/nutrition/meals/{meal_id}`

Important design choice:

The vision model identifies foods and rough portions. The backend handles
nutrition calculation through the local catalog rather than trusting the model
to calculate calories directly.

## Phase 7: Long-Term Memory

Phase 7 added long-term memory with embeddings and Qdrant.

Implemented pieces:

- Qdrant service in Docker Compose.
- Embedding service backed by Ollama.
- Vector store wrapper for Qdrant.
- Memory service for create/search/delete.
- Memory routes under `/api/v1/memory`.
- Automatic memory writes for meals, workout sessions, daily summaries, and body-weight logs when a `user_id` is present.
- Memory write failures are logged and do not block primary DB persistence.

Important files:

- `backend/app/services/memory/embedding_service.py`
- `backend/app/services/memory/vector_store.py`
- `backend/app/services/memory/memory_service.py`
- `backend/app/api/routes/memory.py`
- `backend/app/schemas/memory.py`
- `docs/phase_7_8.md`

Relevant environment variables:

```env
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=fitness_memory
EMBEDDING_MODEL_NAME=nomic-embed-text
```

Representative endpoints:

- `POST /api/v1/memory`
- `POST /api/v1/memory/search`
- `DELETE /api/v1/memory/{memory_id}`

## Phase 8: Meal Image Analysis

Phase 8 implemented the complete meal-photo analysis pipeline.

Implemented pieces:

- Image upload storage service.
- Meal image analyzer service.
- Meal-image prompt template for structured JSON output.
- Meal image analysis route.
- Meal image fields on meals:
  - `image_path`
  - `analysis_status`
  - `analysis_raw_response`
  - `confidence_score`
- Vision-model response parsing with fallback behavior.
- Nutrition estimation from detected foods.
- Analyzed image meal persistence with itemized food records.
- Memory storage for analyzed meals.

Important files:

- `backend/app/services/vision/image_storage.py`
- `backend/app/services/vision/meal_image_analyzer.py`
- `backend/app/services/vision/prompt_templates.py`
- `backend/app/api/routes/meals.py`
- `backend/app/api/routes/ai.py`
- `backend/alembic/versions/20260705_0003_phase_8_meal_image_analysis.py`
- `docs/phase_7_8.md`

Representative endpoints:

- `POST /api/v1/ai/analyze-meal-image`
- `POST /api/v1/meals/analyze-image`

Workflow:

1. Accept an uploaded meal image or base64 image payload.
2. Store the uploaded image locally when using the meal route.
3. Send image base64 to the Ollama vision model.
4. Parse detected foods and confidence.
5. Estimate nutrition through the local nutrition catalog.
6. Save meal and food items in PostgreSQL.
7. Store meal memory in Qdrant when possible.

## Phase 9: Workout Tracking

Phase 9 added normalized workout tracking.

Implemented pieces:

- Exercise catalog table and seed data.
- Workout sessions table.
- Workout exercises table.
- Exercise sets table.
- Workout service with session creation, exercise addition, set addition, updates, deletes, and progress calculation.
- Progress metrics:
  - total sessions
  - total sets
  - total volume
  - best estimated one-rep max
  - best set
  - weekly volume
  - trend
- Workout memory writes to Qdrant.

Important files:

- `backend/app/models/exercise_catalog.py`
- `backend/app/models/workout_session.py`
- `backend/app/models/workout_exercise.py`
- `backend/app/models/exercise_set.py`
- `backend/app/services/workout_service.py`
- `backend/app/api/routes/workouts.py`
- `backend/app/schemas/workout.py`
- `backend/alembic/versions/20260706_0004_phase_9_workout_tracking.py`
- `docs/08_WORKOUTS.md`

Representative endpoints:

- `POST /api/v1/workouts`
- `GET /api/v1/workouts`
- `GET /api/v1/workouts/{workout_id}`
- `PATCH /api/v1/workouts/{workout_id}`
- `DELETE /api/v1/workouts/{workout_id}`
- `POST /api/v1/workouts/{workout_id}/exercises`
- `POST /api/v1/workouts/{workout_id}/exercises/{exercise_id}/sets`
- `GET /api/v1/workouts/progress/{exercise_name}`

## Phase 10: WhatsApp Integration

Phase 10 added local-first WhatsApp webhook support.

Implemented pieces:

- WhatsApp webhook route.
- Webhook parser for simple local payloads and Meta-style payloads.
- Provider interface.
- Mock provider for local development.
- Meta provider scaffold.
- WhatsApp schemas.
- Initial intent handling later replaced by Phase 17 agent delegation.

Important files:

- `backend/app/api/routes/whatsapp.py`
- `backend/app/services/whatsapp/provider_base.py`
- `backend/app/services/whatsapp/webhook_parser.py`
- `backend/app/services/whatsapp/whatsapp_service.py`
- `backend/app/services/whatsapp/providers/mock_provider.py`
- `backend/app/services/whatsapp/providers/meta_provider.py`
- `backend/app/schemas/whatsapp.py`
- `docs/09_WHATSAPP.md`

Relevant environment variables:

```env
WHATSAPP_PROVIDER=mock
WHATSAPP_META_ACCESS_TOKEN=
WHATSAPP_META_PHONE_NUMBER_ID=
WHATSAPP_META_API_BASE_URL=https://graph.facebook.com
WHATSAPP_META_API_VERSION=v20.0
```

Representative endpoint:

- `POST /api/v1/webhooks/whatsapp`

## Phase 11: Daily Summaries, Email, and Scheduling

Phase 11 added daily fitness summaries and email delivery.

Implemented pieces:

- Daily summary generation from meals, workouts, body-weight logs, goals, and user targets.
- Daily summary upsert behavior by user/date.
- Coaching suggestions based on calories, protein, and workout completion.
- Summary email service.
- HTML email template.
- Dry-run behavior when SMTP is disabled.
- Optional scheduled summary email job through APScheduler.
- Summary routes for generating and sending daily summaries.

Important files:

- `backend/app/services/daily_summary_service.py`
- `backend/app/services/email/email_service.py`
- `backend/app/services/email/templates/daily_summary.html`
- `backend/app/services/scheduler/summary_scheduler.py`
- `backend/app/api/routes/summaries.py`
- `backend/app/api/routes/daily_summaries.py`
- `backend/app/schemas/daily_summary.py`
- `backend/app/schemas/email.py`
- `docs/10_PHASE_11_TO_14.md`

Relevant environment variables:

```env
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_TLS=true
SUMMARY_EMAIL_ENABLED=false
SUMMARY_SCHEDULE_ENABLED=false
SUMMARY_SCHEDULE_HOUR=20
SUMMARY_SCHEDULE_MINUTE=0
SUMMARY_SCHEDULE_TIMEZONE=UTC
```

Representative endpoints:

- `GET /api/v1/summaries/daily?user_id=1`
- `POST /api/v1/summaries/daily/send`

## Phase 12: User Profiles and API Key Auth

Phase 12 expanded users into fuller fitness profiles and added optional API-key
authentication.

Implemented pieces:

- User profile fields:
  - phone number
  - age
  - height
  - current weight
  - goal weight
  - activity level
  - fitness goal
  - daily calorie target
  - daily protein target
  - timezone
- Profile read/update endpoints.
- API key settings.
- Request middleware that adds request IDs and enforces API keys when enabled.
- Public endpoint allowlist for docs, health, status, root, and WhatsApp webhooks.

Important files:

- `backend/app/models/user.py`
- `backend/app/schemas/user.py`
- `backend/app/services/user_service.py`
- `backend/app/api/routes/users.py`
- `backend/app/core/middleware.py`
- `backend/alembic/versions/20260706_0005_phase_11_12_summaries_profiles.py`
- `docs/10_PHASE_11_TO_14.md`

Relevant environment variables:

```env
API_KEY_ENABLED=false
API_KEY=
```

Representative endpoints:

- `GET /api/v1/users/{user_id}/profile`
- `PATCH /api/v1/users/{user_id}/profile`

## Phase 13: Production Hardening

Phase 13 improved backend production readiness.

Implemented pieces:

- Pinned direct backend dependencies in `backend/requirements.txt`.
- Dockerfile hardened around a pinned Python image.
- Non-root backend runtime user.
- `.dockerignore` to keep secrets, caches, uploads, and local-only files out of images.
- Standardized error envelope for application, HTTP, validation, and unhandled exceptions.
- Request ID propagation into error responses.

Important files:

- `backend/Dockerfile`
- `backend/requirements.txt`
- `.dockerignore`
- `backend/app/core/exception_handlers.py`
- `backend/app/core/exceptions.py`
- `backend/app/core/middleware.py`
- `docs/10_PHASE_11_TO_14.md`

Standard error shape:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "Resource not found.",
    "details": {},
    "request_id": "..."
  }
}
```

## Phase 14: Observability and Debugging

Phase 14 added service health checks, request IDs, and debug endpoints.

Implemented pieces:

- `X-Request-ID` response header.
- Request ID included in logs.
- Aggregate health endpoint.
- Service-specific health checks for DB, Redis, Qdrant, and Ollama.
- Debug config and service endpoints available only outside production when `DEBUG=true`.
- Status endpoint with basic app metadata.

Important files:

- `backend/app/services/health_service.py`
- `backend/app/api/routes/health.py`
- `backend/app/api/routes/debug.py`
- `backend/app/api/routes/status.py`
- `backend/app/core/logging.py`
- `backend/app/core/middleware.py`
- `backend/app/schemas/health.py`
- `backend/app/schemas/debug.py`
- `docs/10_PHASE_11_TO_14.md`

Representative endpoints:

- `GET /api/v1/health`
- `GET /api/v1/health/db`
- `GET /api/v1/health/redis`
- `GET /api/v1/health/qdrant`
- `GET /api/v1/health/ollama`
- `GET /api/v1/debug/config`
- `GET /api/v1/debug/services`
- `GET /api/v1/status`

## Phase 15: Deployment Prep

Phase 15 prepared the project for local deployment and external exposure.

Implemented pieces:

- Compose stack with persistent volumes for PostgreSQL, Redis, Qdrant, and Ollama.
- Optional Ollama Compose profile.
- Optional Cloudflare Tunnel Compose profile.
- Cloudflare token read from environment at runtime rather than committed to Git.
- PostgreSQL backup and restore scripts.
- README deployment notes.

Important files:

- `docker-compose.yml`
- `scripts/backup_postgres.sh`
- `scripts/restore_postgres.sh`
- `README.md`
- `docs/11_DEPLOYMENT_AND_CI.md`

Persistent volumes:

- `postgres_data`
- `redis_data`
- `qdrant_data`
- `ollama_data`

Cloudflare Tunnel startup pattern:

```bash
docker compose up -d --build
```

The tunnel token lives in the ignored root `.env` file as
`CLOUDFLARE_TUNNEL_TOKEN`.

## Phase 16: Testing and CI

Phase 16 added automated verification and CI scaffolding.

Implemented pieces:

- Pytest configuration.
- Dev requirements file.
- Test suite covering health, meals, memory, workouts, summaries, and the final agent.
- Ruff configuration for linting and formatting.
- GitHub Actions backend workflow.
- README instructions for tests and checks.

Important files:

- `backend/pytest.ini`
- `backend/requirements-dev.txt`
- `backend/tests/conftest.py`
- `backend/tests/test_health.py`
- `backend/tests/test_meals.py`
- `backend/tests/test_memory.py`
- `backend/tests/test_workouts.py`
- `backend/tests/test_summaries.py`
- `backend/tests/test_agent.py`
- `pyproject.toml`
- `.github/workflows/backend.yml`
- `docs/11_DEPLOYMENT_AND_CI.md`

Local verification commands:

```bash
docker compose exec backend python -m pytest -q
ruff check backend
ruff format --check backend
docker compose exec backend alembic check
```

## Phase 17: Final AI Fitness Agent

Phase 17 added the final orchestration layer that ties together the services
implemented in the earlier phases.

Implemented pieces:

- Final `FitnessAgent` class.
- Agent request, response, state, intent, and memory schemas.
- Agent route at `/api/v1/agent/messages`.
- Graph-style control flow:
  1. receive message
  2. classify intent
  3. retrieve memory
  4. route task
  5. generate response
  6. store memory when useful
- Intent handling for:
  - `meal_text`
  - `meal_image`
  - `workout_log`
  - `weight_log`
  - `summary_request`
  - `email_summary`
  - `general_chat`
  - `unknown`
- Memory retrieval before task execution.
- Meal text logging through `MealService`.
- Meal image analysis through `MealImageAnalyzer`, `NutritionService`, and `MealService`.
- Workout logging through `WorkoutService`.
- Weight logging through `BodyWeightLogService`.
- Daily summary generation through `DailySummaryService`.
- Email summary delivery through `EmailService`.
- User lookup through `UserService`.
- WhatsApp webhook delegation into the same agent logic.
- Graceful handling for WhatsApp media IDs/URLs that still need to be downloaded before local analysis.
- Additional tests for core agent intents, meal image behavior, missing media behavior, and WhatsApp delegation.

Important files:

- `backend/app/agents/fitness_agent.py`
- `backend/app/api/routes/agent.py`
- `backend/app/schemas/agent.py`
- `backend/app/api/deps.py`
- `backend/app/services/whatsapp/whatsapp_service.py`
- `backend/app/schemas/whatsapp.py`
- `backend/app/services/memory/memory_service.py`
- `backend/tests/test_agent.py`
- `docs/12_FINAL_AGENT.md`

Representative endpoint:

- `POST /api/v1/agent/messages`

Example request:

```json
{
  "user_id": 1,
  "message_text": "Bench press 50kg 3 sets of 10"
}
```

Example WhatsApp webhook request:

```json
{
  "from": "+15551234567",
  "user_id": 1,
  "type": "text",
  "text": "How am I doing today?"
}
```

## Current Route Inventory

Major route groups now mounted under `/api/v1`:

- `/agent`
- `/ai`
- `/users`
- `/health`
- `/meals`
- `/memory`
- `/nutrition`
- `/webhooks/whatsapp`
- `/workouts`
- `/goals`
- `/daily-summaries`
- `/summaries`
- `/body-weight-logs`
- `/debug`
- `/status`

## Current Database Migration Chain

Current Alembic chain:

1. `20260705_0001_phase_3_initial_tables.py`
2. `20260705_0002_phase_6_nutrition.py`
3. `20260705_0003_phase_8_meal_image_analysis.py`
4. `20260706_0004_phase_9_workout_tracking.py`
5. `20260706_0005_phase_11_12_summaries_profiles.py`

The latest checked migration head was:

```text
20260706_0005
```

## Verification Performed

The latest full verification run completed successfully with:

```text
pytest: 10 passed
ruff check backend: passed
ruff format --check backend: passed
alembic check: no new upgrade operations detected
health endpoint: app/db/redis/qdrant/ollama all ok
```

Live health confirmed:

- DB: ok
- Redis: ok
- Qdrant: ok
- Ollama: ok
- Vision model available: true
- Embedding model available: true

Live smoke tests also verified:

- Agent text meal logging.
- Agent workout logging.
- Agent weight logging.
- Agent daily summary generation.
- Agent email-summary dry run.
- Agent image-media graceful handling.
- WhatsApp webhook delegation to the agent.

Known warnings:

- FastAPI `on_event` deprecation warnings remain.
- Starlette/FastAPI TestClient emits a deprecation warning about `httpx`.

## Current Known Caveats

- WhatsApp image `image_id` and `image_url` are passed into the agent, but media download from WhatsApp/Meta is not yet implemented. The agent returns a clear response asking for `image_base64` or a local `image_path`.
- Email sending is dry-run unless SMTP settings are configured and `SUMMARY_EMAIL_ENABLED=true`.
- Scheduled summaries are disabled unless `SUMMARY_SCHEDULE_ENABLED=true`.
- API key auth is disabled unless `API_KEY_ENABLED=true`.
- The Qdrant Compose image currently uses `qdrant/qdrant:latest`.
- Ollama is expected to run on the host by default unless the optional Compose profile is used.

## High-Level Architecture Now

```text
User / WhatsApp / API
        |
        v
FastAPI routes
        |
        v
FitnessAgent or resource route
        |
        v
Service layer
        |
        +--> PostgreSQL via SQLAlchemy
        +--> Qdrant via memory service
        +--> Ollama for embeddings and vision
        +--> Redis health/infrastructure
        +--> Email service for summaries
```

## Recommended Next Maintenance Items

These are not new phases, just practical cleanup candidates after the current
implementation:

- Replace FastAPI `on_event` startup/shutdown hooks with lifespan handlers.
- Add WhatsApp media download support before image analysis from real WhatsApp messages.
- Pin the Qdrant Docker image to a specific version for production repeatability.
- Add more end-to-end tests around real image uploads once sample images are available.
- Add test coverage for API-key enabled mode.
- Add auth/user identity mapping for real WhatsApp phone numbers instead of relying on local `user_id` payloads.
