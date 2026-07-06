# Phase 10: WhatsApp Integration

Phase 10 adds a local-first WhatsApp webhook and provider abstraction.

Webhook:

- `POST /api/v1/webhooks/whatsapp`

Default provider:

- `WHATSAPP_PROVIDER=mock`

The mock provider logs outbound messages instead of sending to WhatsApp, so the webhook can be tested locally without Meta setup or paid APIs.

Supported local payload shape:

```json
{
  "from": "+15551234567",
  "user_id": 1,
  "type": "text",
  "text": "Logged 3 sets bench press 50kg x 10"
}
```

Initial rule-based intents:

- `meal_image`
- `meal_text`
- `workout_log`
- `weight_log`
- `summary_request`
- `general_chat`
- `unknown`

Text meal and workout messages can be saved when the local webhook payload includes `user_id`. Image, weight, and summary messages are recognized and return clear local-development responses; full media download and agent orchestration are intentionally left for later phases.
