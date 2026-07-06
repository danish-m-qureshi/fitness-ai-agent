# Phase 17: Final AI Fitness Agent

The final agent layer lives under `backend/app/agents/` and orchestrates the
existing services instead of duplicating business logic.

## Agent Endpoint

```http
POST /api/v1/agent/messages
```

Example text meal:

```json
{
  "user_id": 1,
  "message_text": "I ate chicken biryani for lunch"
}
```

Example workout:

```json
{
  "user_id": 1,
  "message_text": "Logged 3 sets bench press 50kg x 10"
}
```

Example weight log:

```json
{
  "user_id": 1,
  "message_text": "My weight is 82.4kg today"
}
```

Example daily summary:

```json
{
  "user_id": 1,
  "message_text": "How am I doing today?"
}
```

Meal image analysis accepts `image_base64` or `image_path`:

```json
{
  "user_id": 1,
  "image_path": "storage/uploads/meals/example.jpg"
}
```

WhatsApp-style image messages can include `image_id` or `image_url`, but those
must be downloaded to `image_base64` or a local `image_path` before the local
vision model can analyze them.

Example email summary:

```json
{
  "user_id": 1,
  "message_text": "Email me today's summary"
}
```

## Agent Flow

The agent executes explicit graph-style nodes:

1. receive message
2. classify intent
3. retrieve memory
4. route to the correct service
5. generate response
6. store agent note when useful

Supported intents:

- `meal_text`
- `meal_image`
- `workout_log`
- `weight_log`
- `summary_request`
- `email_summary`
- `general_chat`
- `unknown`

## WhatsApp

The WhatsApp webhook now delegates to the same agent endpoint logic. That means
mock WhatsApp payloads can log meals, workouts, body weight, and summaries
through the same orchestration path as direct API calls. Image media identifiers
are passed into the agent and return a clear local-download requirement until a
WhatsApp media download step is added.

## Email Summaries

The final agent can classify email summary requests, generate the daily summary
through `DailySummaryService`, load the user through `UserService`, and send
through `EmailService`. With SMTP disabled, this returns a dry-run response;
with SMTP enabled, the existing email service sends the message and marks the
summary as emailed.
