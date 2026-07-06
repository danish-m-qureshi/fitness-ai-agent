# Phase 18: Real WhatsApp Integration Hardening

Last updated: 2026-07-06

Phase 18 hardens the WhatsApp path for real Meta webhook traffic while keeping
the local mock workflow intact. It does not rewrite the final agent
architecture.

## What Changed

### Phone Number to User Mapping

Incoming WhatsApp messages now resolve the sender phone number to
`users.phone_number`.

Behavior:

- Local test payloads may still pass `user_id` as a development shortcut.
- If `user_id` is absent, the webhook uses the WhatsApp sender phone number.
- Phone numbers are normalized before lookup.
- New or updated user profile phone numbers are normalized by schema validators.
- Existing unnormalized rows are still tolerated by a fallback lookup.
- Unknown phone numbers receive onboarding guidance instead of causing a server
  error.

Unknown-user error code:

```text
whatsapp_user_not_found
```

### Meta Media Download

Image webhooks with a WhatsApp media ID now go through a download step before
the final agent is called.

Flow:

```text
Meta webhook image media ID
        ↓
fetch media metadata from Meta
        ↓
extract temporary media URL
        ↓
download media bytes with Authorization header
        ↓
validate MIME type and size
        ↓
store through ImageStorageService
        ↓
pass local image_path to FitnessAgent
        ↓
existing image meal analysis flow runs
```

The media downloader is implemented in:

```text
backend/app/services/whatsapp/media_downloader.py
```

The webhook orchestration is implemented in:

```text
backend/app/services/whatsapp/whatsapp_service.py
```

### Image Safety

Allowed image MIME types:

```text
image/jpeg
image/png
image/webp
```

The existing `MAX_IMAGE_UPLOAD_BYTES` / `max_image_upload_bytes` setting is used
to enforce the maximum WhatsApp image size.

Clean error codes:

```text
whatsapp_media_download_failed
whatsapp_media_too_large
whatsapp_unsupported_media_type
```

The code does not log:

- Meta access tokens
- temporary media URLs
- raw image bytes

On media download failure, the webhook returns a user-friendly WhatsApp reply
and logs the internal reason with the current request ID.

### Agent Integration

After successful media download, the webhook calls the existing final
`FitnessAgent` with a local `image_path`.

That means the existing flow remains responsible for:

- vision analysis
- nutrition estimation
- meal persistence
- memory storage
- WhatsApp reply generation

No duplicate meal-analysis business logic was added to the WhatsApp layer.

### Local Mock Behavior

The mock provider still works for local text webhook tests.

For image testing without Meta, either:

- pass a local `image_path` in the local payload, or
- unit-test the downloader with mocked HTTP responses.

Local `user_id` remains supported as a development shortcut.

## Important Files

New or changed files:

- `backend/app/core/phone_numbers.py`
- `backend/app/schemas/user.py`
- `backend/app/services/user_service.py`
- `backend/app/services/vision/image_storage.py`
- `backend/app/services/whatsapp/media_downloader.py`
- `backend/app/services/whatsapp/whatsapp_service.py`
- `backend/app/schemas/whatsapp.py`
- `backend/app/api/deps.py`
- `backend/tests/test_whatsapp_integration.py`
- `backend/tests/test_agent.py`
- `backend/Dockerfile`

## Required Environment Variables

For local mock mode:

```env
WHATSAPP_PROVIDER=mock
```

For real Meta WhatsApp sending and media download:

```env
WHATSAPP_PROVIDER=meta
WHATSAPP_META_ACCESS_TOKEN=<meta-access-token>
WHATSAPP_META_PHONE_NUMBER_ID=<meta-phone-number-id>
WHATSAPP_META_API_BASE_URL=https://graph.facebook.com
WHATSAPP_META_API_VERSION=v20.0
MAX_IMAGE_UPLOAD_BYTES=8388608
```

Related local model settings:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
VISION_MODEL=qwen3-vl:8b
EMBEDDING_MODEL_NAME=nomic-embed-text
```

Do not commit real Meta tokens.

## Local Testing

Start the stack:

```bash
docker compose up -d --build
```

Run migrations:

```bash
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend alembic check
```

Run tests and lint:

```bash
docker compose exec -T backend python -m pytest -q
docker compose exec -T backend python -m ruff check .
docker compose exec -T backend python -m ruff format --check .
```

Create or update a user with a WhatsApp phone number:

```json
{
  "name": "WhatsApp User",
  "phone_number": "+15551234567"
}
```

Test text webhook without `user_id`:

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "from": "15551234567",
    "type": "text",
    "text": "I ate chicken rice"
  }'
```

Expected:

- sender phone maps to the existing user
- final agent handles the text
- mock provider logs/sends a reply

Test unknown phone:

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "from": "15550000000",
    "type": "text",
    "text": "I ate chicken rice"
  }'
```

Expected:

```text
error_code: whatsapp_user_not_found
```

The reply should ask the user to create or update their profile with the
WhatsApp number.

## Meta Image Webhook Shape

Meta-style image payloads are parsed from the existing webhook parser. The
important fields are:

```json
{
  "entry": [
    {
      "changes": [
        {
          "value": {
            "messages": [
              {
                "from": "15551234567",
                "type": "image",
                "image": {
                  "id": "MEDIA_ID_FROM_META"
                }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

The backend uses the media ID to call the Meta Graph API. It does not trust or
log temporary media URLs.

## Remaining Limitations

- This phase downloads inbound media for analysis, but does not implement
  outbound WhatsApp image sending.
- Real Meta webhook verification/challenge handling is not expanded here.
- Unknown phone numbers receive onboarding guidance, but a full onboarding flow
  is not implemented.
- Phone normalization is intentionally simple and E.164-like. It is good enough
  for MVP matching, but a dedicated phone-number library could be added later.
- Cloudflare Tunnel was not started by this phase.
- Strict outbound Cloudflare Gateway policies were not enabled.

## Security Notes

- Keep `DEBUG=false` before public exposure.
- Enable API-key protection before exposing non-webhook endpoints publicly.
- Keep real Meta tokens in `.env` or deployment secrets only.
- Avoid logging raw webhook media URLs or binary content.
- Continue to start Cloudflare Gateway with visibility/DNS security first, not a
  strict allowlist.
