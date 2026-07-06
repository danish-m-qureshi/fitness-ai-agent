import logging

from app.services.whatsapp.provider_base import WhatsAppProvider

logger = logging.getLogger(__name__)


class MockWhatsAppProvider(WhatsAppProvider):
    name = "mock"

    async def send_text(self, to: str, message: str) -> None:
        logger.info("Mock WhatsApp text to=%s message=%s", to, message)

    async def send_image(
        self,
        to: str,
        image_path: str,
        caption: str | None = None,
    ) -> None:
        logger.info(
            "Mock WhatsApp image to=%s image_path=%s caption=%s",
            to,
            image_path,
            caption,
        )
