# Phases 11-14

## Phase 11: Email and Scheduled Summaries

- `GET /api/v1/summaries/daily?user_id=1` generates or updates a daily summary.
- `POST /api/v1/summaries/daily/send` sends the summary by email or returns a dry-run result when SMTP is disabled.
- SMTP is disabled by default. Configure `SMTP_*` and `SUMMARY_EMAIL_ENABLED=true` to send real email.
- The scheduler is disabled by default. Enable it with `SUMMARY_SCHEDULE_ENABLED=true`.

## Phase 12: Authentication and User Profiles

- Users now include profile fields for phone, age, height, weight, goals, macro targets, and timezone.
- `GET /api/v1/users/{user_id}/profile` returns profile data.
- `PATCH /api/v1/users/{user_id}/profile` updates profile-only fields.
- API-key auth is controlled by `API_KEY_ENABLED` and `API_KEY`.
- When enabled, send `X-API-Key: <key>` for non-public endpoints.

Public endpoints:

- `/`
- `/docs`
- `/openapi.json`
- `/api/v1/health*`
- `/api/v1/status`
- `/api/v1/webhooks/whatsapp`

## Phase 13: Production Hardening

- Docker now uses a pinned Python image and non-root runtime user.
- Direct backend dependencies are pinned in `backend/requirements.txt`.
- `.dockerignore` excludes secrets, caches, uploads, and local environments.
- App errors now use a standard envelope:

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

- Every response includes `X-Request-ID`.
- Logs include the same request ID.
- Service checks:
  - `GET /api/v1/health`
  - `GET /api/v1/health/db`
  - `GET /api/v1/health/redis`
  - `GET /api/v1/health/qdrant`
  - `GET /api/v1/health/ollama`
- Debug endpoints are available only when not production and `DEBUG=true`:
  - `GET /api/v1/debug/config`
  - `GET /api/v1/debug/services`
