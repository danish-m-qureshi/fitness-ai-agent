import httpx
from app.core.exceptions import AppException
from app.services.whatsapp.provider_base import WhatsAppProvider


class MetaWhatsAppProvider(WhatsAppProvider):
    name = "meta"

    def __init__(
        self,
        access_token: str | None,
        phone_number_id: str | None,
        api_base_url: str,
        api_version: str,
    ) -> None:
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_base_url = api_base_url.rstrip("/")
        self.api_version = api_version.strip("/")

    async def send_text(self, to: str, message: str) -> None:
        self._ensure_configured()
        await self._post_message(
            {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message},
            }
        )

    async def send_image(
        self,
        to: str,
        image_path: str,
        caption: str | None = None,
    ) -> None:
        self._ensure_configured()
        raise AppException(
            message=(
                "Meta WhatsApp image sending requires media upload support, "
                "which is not enabled in the local-first Phase 10 provider."
            ),
            status_code=501,
            error_code="whatsapp_image_send_not_implemented",
        )

    async def _post_message(self, payload: dict) -> None:
        url = f"{self.api_base_url}/{self.api_version}/{self.phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AppException(
                message="Meta WhatsApp send failed.",
                status_code=502,
                error_code="whatsapp_meta_send_failed",
            ) from exc

    def _ensure_configured(self) -> None:
        if not self.access_token or not self.phone_number_id:
            raise AppException(
                message="Meta WhatsApp provider is not configured.",
                status_code=500,
                error_code="whatsapp_meta_not_configured",
            )
