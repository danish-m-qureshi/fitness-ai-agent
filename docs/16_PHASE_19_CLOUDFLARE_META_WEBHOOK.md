# Phase 19: Cloudflare Tunnel + Meta Webhook Setup

## What Changed

Phase 19 hardens the app for exposing the WhatsApp webhook through Cloudflare
Tunnel without exposing the rest of the API by default.

Implemented changes:

- Added Meta webhook GET verification at:

  ```text
  GET /api/v1/webhooks/whatsapp
  ```

- The webhook verification endpoint accepts Meta's `hub.mode`,
  `hub.verify_token`, and `hub.challenge` query parameters.
- The endpoint returns the raw challenge only when `hub.mode=subscribe` and the
  token matches `WHATSAPP_META_VERIFY_TOKEN`.
- API-key middleware now treats only `/api/v1/webhooks/whatsapp` as public when
  `API_KEY_ENABLED=true`.
- Non-webhook routes require `X-API-Key: <API_KEY>` when API-key auth is
  enabled.
- FastAPI docs and OpenAPI can now be disabled with `DOCS_ENABLED=false`.
- Debug endpoints remain unavailable when `DEBUG=false` or
  `ENVIRONMENT=production`.
- The Docker healthcheck sends `X-API-Key` automatically when API-key auth is
  enabled and `API_KEY` is configured.
- The Cloudflare Tunnel Compose service waits for a healthy backend before
  starting.

## Required Environment Variables

Set these before public webhook exposure:

```env
ENVIRONMENT=production
DEBUG=false
DOCS_ENABLED=false

API_KEY_ENABLED=true
API_KEY=<strong-random-api-key>

WHATSAPP_PROVIDER=meta
WHATSAPP_META_ACCESS_TOKEN=<meta-whatsapp-access-token>
WHATSAPP_META_PHONE_NUMBER_ID=<meta-phone-number-id>
WHATSAPP_META_VERIFY_TOKEN=<meta-webhook-verify-token>
WHATSAPP_META_API_BASE_URL=https://graph.facebook.com
WHATSAPP_META_API_VERSION=v20.0

CLOUDFLARE_TUNNEL_TOKEN=<cloudflare-tunnel-token>
```

Do not commit real values. Keep them in an ignored environment file or export
them in the shell that starts Docker Compose.

## Cloudflare Tunnel

Cloudflare Tunnel is part of the default local Compose stack. Keep the token in
the ignored root `.env` file:

```env
CLOUDFLARE_TUNNEL_TOKEN=<cloudflare-tunnel-token>
```

Start the stack:

```bash
docker compose up -d --build
docker compose exec -T backend alembic upgrade head
```

In Cloudflare Zero Trust, point the tunnel's public hostname to:

```text
http://backend:8000
```

The public Meta callback URL should be:

```text
https://<your-cloudflare-hostname>/api/v1/webhooks/whatsapp
```

## Meta Webhook Verification

In the Meta developer dashboard:

- Callback URL:

  ```text
  https://<your-cloudflare-hostname>/api/v1/webhooks/whatsapp
  ```

- Verify token:

  ```text
  WHATSAPP_META_VERIFY_TOKEN
  ```

Local verification example:

```bash
curl -G "http://localhost:8000/api/v1/webhooks/whatsapp" \
  --data-urlencode "hub.mode=subscribe" \
  --data-urlencode "hub.verify_token=<meta-webhook-verify-token>" \
  --data-urlencode "hub.challenge=local-challenge"
```

Expected response body:

```text
local-challenge
```

## API-Key Protection

With `API_KEY_ENABLED=true`, this remains public for Meta:

```text
/api/v1/webhooks/whatsapp
```

Everything else requires:

```http
X-API-Key: <API_KEY>
```

Example:

```bash
curl http://localhost:8000/api/v1/health \
  -H "X-API-Key: <strong-random-api-key>"
```

## Docs, OpenAPI, and Debug Routes

Recommended public settings:

```env
DEBUG=false
DOCS_ENABLED=false
ENVIRONMENT=production
```

With those settings:

- `/docs` is disabled.
- `/openapi.json` is disabled.
- `/api/v1/debug/config` returns 404.
- `/api/v1/debug/services` returns 404.

## Verification Checklist

Run:

```bash
docker compose up -d --build
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend alembic check
docker compose exec -T backend python -m pytest -q
docker compose exec -T backend python -m ruff check .
docker compose exec -T backend python -m ruff format --check .
```

Then verify with your configured API key:

```bash
curl http://localhost:8000/api/v1/health \
  -H "X-API-Key: <strong-random-api-key>"
```

And verify the Meta challenge endpoint:

```bash
curl -G "https://<your-cloudflare-hostname>/api/v1/webhooks/whatsapp" \
  --data-urlencode "hub.mode=subscribe" \
  --data-urlencode "hub.verify_token=<meta-webhook-verify-token>" \
  --data-urlencode "hub.challenge=cloudflare-check"
```

Expected response body:

```text
cloudflare-check
```

## Remaining Limitations

- Cloudflare routing is still configured in the Cloudflare dashboard; the app
  protects non-webhook routes with API-key auth but cannot restrict dashboard
  tunnel routes by itself.
- Meta request signature verification is not part of Phase 19. It remains a
  Phase 23 security hardening item.
- Docker images are not fully pinned yet. Qdrant and cloudflared still use
  `latest`.
- The tunnel token is intentionally not stored in committed files.
