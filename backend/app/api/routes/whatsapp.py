import hmac

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.api.deps import get_whatsapp_service
from app.core.config import Settings, get_settings
from app.core.exceptions import AppException
from app.schemas.whatsapp import WhatsAppWebhookPayload, WhatsAppWebhookResponse
from app.services.whatsapp.whatsapp_service import WhatsAppService

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])


@router.get("", response_class=PlainTextResponse)
async def verify_whatsapp_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    if not settings.whatsapp_meta_verify_token:
        raise AppException(
            message="WhatsApp webhook verify token is not configured.",
            status_code=503,
            error_code="whatsapp_verify_token_not_configured",
        )

    if (
        mode == "subscribe"
        and challenge
        and verify_token
        and hmac.compare_digest(
            verify_token,
            settings.whatsapp_meta_verify_token,
        )
    ):
        return PlainTextResponse(challenge)

    raise AppException(
        message="WhatsApp webhook verification failed.",
        status_code=403,
        error_code="whatsapp_webhook_verification_failed",
    )


@router.post("", response_model=WhatsAppWebhookResponse)
async def receive_whatsapp_webhook(
    payload: WhatsAppWebhookPayload,
    whatsapp_service: WhatsAppService = Depends(get_whatsapp_service),
) -> WhatsAppWebhookResponse:
    return await whatsapp_service.handle_webhook(payload)
