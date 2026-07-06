from app.api.deps import get_whatsapp_service
from app.schemas.whatsapp import WhatsAppWebhookPayload, WhatsAppWebhookResponse
from app.services.whatsapp.whatsapp_service import WhatsAppService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])


@router.post("", response_model=WhatsAppWebhookResponse)
async def receive_whatsapp_webhook(
    payload: WhatsAppWebhookPayload,
    whatsapp_service: WhatsAppService = Depends(get_whatsapp_service),
) -> WhatsAppWebhookResponse:
    return await whatsapp_service.handle_webhook(payload)
