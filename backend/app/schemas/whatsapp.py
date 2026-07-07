from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

WhatsAppIntent = Literal[
    "meal_image",
    "meal_text",
    "workout_log",
    "weight_log",
    "summary_request",
    "email_summary",
    "general_chat",
    "unknown",
]


class WhatsAppWebhookPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    from_number: str | None = Field(default=None, alias="from")
    sender: str | None = None
    phone_number: str | None = None
    user_id: int | None = Field(default=None, ge=1)
    type: str | None = None
    message_type: str | None = None
    text: str | None = None
    image_url: str | None = None
    image_id: str | None = None
    image_path: str | None = None
    message_id: str | None = None
    whatsapp_message_id: str | None = None


class IncomingWhatsAppMessage(BaseModel):
    sender: str
    user_id: int | None = None
    message_type: str
    text: str | None = None
    image_id: str | None = None
    image_url: str | None = None
    image_path: str | None = None
    whatsapp_message_id: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class WhatsAppWebhookResponse(BaseModel):
    status: Literal["received", "ignored", "error"]
    provider: str
    intent: WhatsAppIntent
    sender: str | None = None
    reply: str | None = None
    meal_id: int | None = None
    workout_id: int | None = None
    weight_log_id: int | None = None
    daily_summary_id: int | None = None
    error: str | None = None
    error_code: str | None = None
