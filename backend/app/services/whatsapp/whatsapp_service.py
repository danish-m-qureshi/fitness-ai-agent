import logging

from app.agents.fitness_agent import FitnessAgent
from app.core.exceptions import AppException
from app.core.middleware import request_id_context
from app.schemas.agent import AgentRequest
from app.schemas.whatsapp import WhatsAppWebhookPayload, WhatsAppWebhookResponse
from app.services.user_service import UserService
from app.services.whatsapp.media_downloader import WhatsAppMediaDownloader
from app.services.whatsapp.provider_base import WhatsAppProvider
from app.services.whatsapp.webhook_parser import WhatsAppWebhookParser

logger = logging.getLogger(__name__)

ONBOARDING_REPLY = (
    "I received your WhatsApp message, but I do not recognize this phone number yet. "
    "Please create or update your fitness profile with this WhatsApp number before "
    "logging meals, workouts, or summaries."
)
MEDIA_DOWNLOAD_REPLY = (
    "I received your image, but I could not download it safely for local analysis. "
    "Please try again with a JPEG, PNG, or WebP image."
)


class WhatsAppService:
    def __init__(
        self,
        provider: WhatsAppProvider,
        agent: FitnessAgent,
        user_service: UserService,
        media_downloader: WhatsAppMediaDownloader | None = None,
    ) -> None:
        self.provider = provider
        self.agent = agent
        self.user_service = user_service
        self.media_downloader = media_downloader
        self.parser = WhatsAppWebhookParser()

    async def handle_webhook(
        self,
        payload: WhatsAppWebhookPayload,
    ) -> WhatsAppWebhookResponse:
        incoming = self.parser.parse(payload)
        user_id = self._resolve_user_id(
            local_user_id=incoming.user_id,
            sender=incoming.sender,
        )
        if user_id is None:
            return await self._reply_with_error(
                sender=incoming.sender,
                reply=ONBOARDING_REPLY,
                intent="unknown",
                error=ONBOARDING_REPLY,
                error_code="whatsapp_user_not_found",
            )

        image_path = incoming.image_path
        if self._is_image_message(incoming.message_type) and image_path is None:
            media_result = await self._download_media_if_needed(
                sender=incoming.sender,
                image_id=incoming.image_id,
            )
            if isinstance(media_result, WhatsAppWebhookResponse):
                return media_result

            image_path = media_result

        agent_response = await self.agent.run(
            AgentRequest(
                user_id=user_id,
                message_text=incoming.text,
                image_path=image_path,
                channel="whatsapp",
                sender=incoming.sender,
            )
        )
        reply = agent_response.response_text

        if incoming.sender and reply:
            await self.provider.send_text(incoming.sender, reply)

        return WhatsAppWebhookResponse(
            status="received",
            provider=self.provider.name,
            intent=agent_response.intent,
            sender=incoming.sender,
            reply=reply,
            meal_id=agent_response.meal_id,
            workout_id=agent_response.workout_id,
            weight_log_id=agent_response.weight_log_id,
            daily_summary_id=agent_response.daily_summary_id,
            error="; ".join(agent_response.errors) or None,
        )

    def _resolve_user_id(
        self,
        local_user_id: int | None,
        sender: str,
    ) -> int | None:
        if local_user_id is not None:
            return local_user_id

        user = self.user_service.get_user_by_phone_number(sender)
        return user.id if user is not None else None

    async def _download_media_if_needed(
        self,
        sender: str,
        image_id: str | None,
    ) -> str | WhatsAppWebhookResponse:
        if not image_id:
            return await self._reply_with_error(
                sender=sender,
                reply=MEDIA_DOWNLOAD_REPLY,
                intent="meal_image",
                error="WhatsApp image payload did not include a media ID.",
                error_code="whatsapp_media_download_failed",
            )

        if self.media_downloader is None:
            return await self._reply_with_error(
                sender=sender,
                reply=MEDIA_DOWNLOAD_REPLY,
                intent="meal_image",
                error="WhatsApp media downloader is not configured.",
                error_code="whatsapp_media_download_failed",
            )

        try:
            downloaded_media = await self.media_downloader.download_image(image_id)
        except AppException as exc:
            logger.warning(
                "WhatsApp media download failed request_id=%s error_code=%s reason=%s",
                request_id_context.get(),
                exc.error_code,
                exc.message,
            )
            return await self._reply_with_error(
                sender=sender,
                reply=self._media_failure_reply(exc),
                intent="meal_image",
                error=exc.message,
                error_code=exc.error_code,
            )

        return downloaded_media.stored_image.path

    async def _reply_with_error(
        self,
        sender: str | None,
        reply: str,
        intent: str,
        error: str,
        error_code: str,
    ) -> WhatsAppWebhookResponse:
        if sender and reply:
            await self.provider.send_text(sender, reply)

        return WhatsAppWebhookResponse(
            status="received",
            provider=self.provider.name,
            intent=intent,  # type: ignore[arg-type]
            sender=sender,
            reply=reply,
            error=error,
            error_code=error_code,
        )

    def _media_failure_reply(self, exc: AppException) -> str:
        if exc.error_code == "whatsapp_media_too_large":
            return "That image is too large for local analysis. Please send a smaller JPEG, PNG, or WebP image."

        if exc.error_code == "whatsapp_unsupported_media_type":
            return "I can only analyze JPEG, PNG, or WebP meal images right now."

        return MEDIA_DOWNLOAD_REPLY

    def _is_image_message(self, message_type: str) -> bool:
        return message_type.lower().strip() == "image"
