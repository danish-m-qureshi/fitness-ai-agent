# Phase 20: Real WhatsApp Text Messaging

## What Changed

Phase 20 completes the real WhatsApp text-message path through the existing
agent architecture.

Implemented behavior:

- Meta WhatsApp text webhook payloads are parsed into local incoming messages.
- Sender phone numbers are resolved against `users.phone_number`.
- Known users are delegated to `FitnessAgent` with `channel="whatsapp"`.
- Agent replies are sent back through the configured WhatsApp provider.
- Text flows persist through existing services:
  - meals
  - workouts
  - body weight logs
  - daily summaries
- Unknown phone numbers receive onboarding guidance instead of failing.
- Meta delivery/read status callbacks are ignored cleanly and are not sent to
  the agent.
- Outbound Meta reply failures are logged but do not make webhook POST handling
  fail. This keeps Meta dashboard sample payloads and fake sender numbers from
  receiving a `502 Bad Gateway` response.
- `MetaWhatsAppProvider` now supports an injectable HTTP client for tests while
  keeping normal runtime behavior unchanged.

## Webhook POST Robustness Fix

During live Meta dashboard testing, GET webhook verification succeeded but the
dashboard's sample `POST /api/v1/webhooks/whatsapp` returned `502 Bad Gateway`.

The backend logs showed that inbound parsing worked. The failure happened after
that, when the app attempted to send an outbound WhatsApp reply to Meta and Meta
returned `400 Bad Request` for the sample/fake sender. That provider error was
escaping the webhook request as `whatsapp_meta_send_failed`.

The webhook now treats outbound replies as best effort:

- Known users still route to `FitnessAgent`.
- Unknown users still produce onboarding copy.
- The app attempts to send the WhatsApp reply when possible.
- If Meta rejects the outbound reply, the backend logs the request ID and error
  code, then still returns a safe received webhook response to Meta.

This prevents Meta webhook retries caused by reply-send failures while keeping
the internal failure visible in logs.

## Required Environment Variables

For real Meta text messaging:

```env
WHATSAPP_PROVIDER=meta
WHATSAPP_META_ACCESS_TOKEN=<meta-whatsapp-access-token>
WHATSAPP_META_PHONE_NUMBER_ID=<meta-phone-number-id>
WHATSAPP_META_VERIFY_TOKEN=<meta-webhook-verify-token>
WHATSAPP_META_API_BASE_URL=https://graph.facebook.com
WHATSAPP_META_API_VERSION=v20.0
```

For public exposure through Phase 19:

```env
ENVIRONMENT=production
DEBUG=false
DOCS_ENABLED=false
API_KEY_ENABLED=true
API_KEY=<strong-random-api-key>
CLOUDFLARE_TUNNEL_TOKEN=<cloudflare-tunnel-token>
```

Do not commit real token values.

## User Setup

The incoming Meta sender is matched against `users.phone_number`. Store the
WhatsApp number on the user profile in international format.

Example local update:

```bash
curl -X PATCH "http://localhost:8000/api/v1/users/1/profile" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api-key-if-enabled>" \
  -d '{"phone_number":"+15551234567"}'
```

The backend normalizes common phone-number formats during lookup, so
`+1 (555) 123-4567` and `15551234567` resolve to the same user.

## Local Text Webhook Test

With `WHATSAPP_PROVIDER=mock`, you can test parsing and persistence locally
without sending a real WhatsApp reply:

```bash
curl -X POST "http://localhost:8000/api/v1/webhooks/whatsapp" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [
      {
        "id": "waba-id",
        "changes": [
          {
            "field": "messages",
            "value": {
              "messaging_product": "whatsapp",
              "metadata": {
                "display_phone_number": "15557654321",
                "phone_number_id": "phone-number-id"
              },
              "contacts": [
                {
                  "profile": {"name": "Local User"},
                  "wa_id": "15551234567"
                }
              ],
              "messages": [
                {
                  "from": "15551234567",
                  "id": "wamid.local-text",
                  "timestamp": "1790000000",
                  "text": {"body": "I ate chicken biryani for lunch"},
                  "type": "text"
                }
              ]
            }
          }
        ]
      }
    ]
  }'
```

Expected response includes:

```json
{
  "status": "received",
  "intent": "meal_text",
  "meal_id": 1
}
```

## Real Meta Flow

1. Meta sends a text webhook to:

   ```text
   https://<your-cloudflare-hostname>/api/v1/webhooks/whatsapp
   ```

2. The parser extracts:

   ```text
   messages[0].from
   messages[0].text.body
   messages[0].type
   ```

3. `WhatsAppService` resolves the sender phone number.
4. `FitnessAgent` classifies and persists the request.
5. `MetaWhatsAppProvider` sends the reply to:

   ```text
   https://graph.facebook.com/<version>/<phone-number-id>/messages
   ```

## Tested Text Cases

Automated tests cover:

- Meal logging from a real Meta-shaped text webhook.
- Workout logging from a real Meta-shaped text webhook.
- Weight logging from a real Meta-shaped text webhook.
- Daily summary request from a real Meta-shaped text webhook.
- Unknown phone onboarding.
- Meta dashboard sample message payload with an unknown/fake sender.
- Outbound Meta reply failure without webhook `502`.
- Meta status callback ignored without an agent reply.
- Meta provider outbound text request shape.

## Verification

Run:

```bash
docker compose up -d --build
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend alembic check
docker compose exec -T backend python -m pytest -q
docker compose exec -T backend python -m ruff check .
docker compose exec -T backend python -m ruff format --check .
```

## Remaining Limitations

- Real image analysis belongs to Phase 21.
- Meta webhook signature verification is still a Phase 23 hardening item.
- Delivery/read status callbacks are ignored, not stored for analytics.
- The local intent classifier is rule-based and intentionally simple until the
  Phase 24 agent-quality pass.
