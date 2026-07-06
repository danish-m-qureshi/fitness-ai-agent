import mimetypes
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx
from app.core.exceptions import AppException
from app.services.vision.image_storage import (
    SAFE_IMAGE_CONTENT_TYPES,
    ImageStorageService,
    StoredImage,
)


@dataclass(frozen=True)
class DownloadedWhatsAppMedia:
    media_id: str
    stored_image: StoredImage
    metadata_content_type: str | None = None


class WhatsAppMediaDownloader:
    def __init__(
        self,
        access_token: str | None,
        api_base_url: str,
        api_version: str,
        image_storage_service: ImageStorageService,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.access_token = access_token
        self.api_base_url = api_base_url.rstrip("/")
        self.api_version = api_version.strip("/")
        self.image_storage_service = image_storage_service
        self.http_client = http_client
        self.timeout_seconds = timeout_seconds

    async def download_image(self, media_id: str) -> DownloadedWhatsAppMedia:
        self._ensure_configured()
        async with self._client_context() as client:
            metadata = await self._fetch_metadata(client, media_id)
            media_url = self._metadata_url(metadata)
            metadata_content_type = self._metadata_content_type(metadata)
            self._validate_content_type(metadata_content_type)
            self._validate_metadata_size(metadata)

            image_bytes, download_content_type = await self._download_media_bytes(
                client=client,
                media_url=media_url,
                metadata_content_type=metadata_content_type,
            )

        stored_image = self.image_storage_service.save_meal_image_bytes(
            image_bytes=image_bytes,
            content_type=download_content_type,
            original_filename=self._filename(media_id, download_content_type),
        )
        return DownloadedWhatsAppMedia(
            media_id=media_id,
            stored_image=stored_image,
            metadata_content_type=metadata_content_type,
        )

    async def _fetch_metadata(
        self,
        client: httpx.AsyncClient,
        media_id: str,
    ) -> dict:
        url = f"{self.api_base_url}/{self.api_version}/{media_id}"
        try:
            response = await client.get(url, headers=self._auth_headers())
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AppException(
                message="Could not fetch WhatsApp media metadata.",
                status_code=502,
                error_code="whatsapp_media_download_failed",
            ) from exc

        if not isinstance(payload, dict):
            raise AppException(
                message="WhatsApp media metadata response was invalid.",
                status_code=502,
                error_code="whatsapp_media_download_failed",
            )

        return payload

    async def _download_media_bytes(
        self,
        client: httpx.AsyncClient,
        media_url: str,
        metadata_content_type: str | None,
    ) -> tuple[bytes, str]:
        try:
            async with client.stream(
                "GET",
                media_url,
                headers=self._auth_headers(),
                follow_redirects=True,
            ) as response:
                response.raise_for_status()
                content_type = self._normalized_content_type(
                    response.headers.get("content-type") or metadata_content_type
                )
                self._validate_content_type(content_type)
                self._validate_content_length(response.headers.get("content-length"))

                chunks: list[bytes] = []
                total_bytes = 0
                async for chunk in response.aiter_bytes():
                    if not chunk:
                        continue
                    total_bytes += len(chunk)
                    if total_bytes > self.image_storage_service.max_image_bytes:
                        raise AppException(
                            message="WhatsApp media image is too large.",
                            status_code=413,
                            error_code="whatsapp_media_too_large",
                        )
                    chunks.append(chunk)
        except AppException:
            raise
        except httpx.HTTPError as exc:
            raise AppException(
                message="Could not download WhatsApp media.",
                status_code=502,
                error_code="whatsapp_media_download_failed",
            ) from exc

        image_bytes = b"".join(chunks)
        if not image_bytes:
            raise AppException(
                message="Downloaded WhatsApp media was empty.",
                status_code=502,
                error_code="whatsapp_media_download_failed",
            )

        return image_bytes, content_type

    def _metadata_url(self, metadata: dict) -> str:
        media_url = metadata.get("url")
        if not isinstance(media_url, str) or not media_url.strip():
            raise AppException(
                message="WhatsApp media metadata did not include a download URL.",
                status_code=502,
                error_code="whatsapp_media_download_failed",
            )

        return media_url

    def _metadata_content_type(self, metadata: dict) -> str | None:
        mime_type = metadata.get("mime_type")
        if isinstance(mime_type, str):
            return self._normalized_content_type(mime_type)

        return None

    def _validate_metadata_size(self, metadata: dict) -> None:
        raw_file_size = metadata.get("file_size")
        if raw_file_size is None:
            return

        try:
            file_size = int(raw_file_size)
        except (TypeError, ValueError) as exc:
            raise AppException(
                message="WhatsApp media metadata had an invalid file size.",
                status_code=502,
                error_code="whatsapp_media_download_failed",
            ) from exc

        if file_size > self.image_storage_service.max_image_bytes:
            raise AppException(
                message="WhatsApp media image is too large.",
                status_code=413,
                error_code="whatsapp_media_too_large",
            )

    def _validate_content_length(self, content_length: str | None) -> None:
        if content_length is None:
            return

        try:
            file_size = int(content_length)
        except ValueError as exc:
            raise AppException(
                message="WhatsApp media download had an invalid content length.",
                status_code=502,
                error_code="whatsapp_media_download_failed",
            ) from exc

        if file_size > self.image_storage_service.max_image_bytes:
            raise AppException(
                message="WhatsApp media image is too large.",
                status_code=413,
                error_code="whatsapp_media_too_large",
            )

    def _validate_content_type(self, content_type: str | None) -> None:
        if content_type not in SAFE_IMAGE_CONTENT_TYPES:
            raise AppException(
                message="Unsupported WhatsApp media type. Send a JPEG, PNG, or WebP image.",
                status_code=415,
                error_code="whatsapp_unsupported_media_type",
            )

    def _normalized_content_type(self, content_type: str | None) -> str | None:
        if content_type is None:
            return None

        return content_type.split(";", 1)[0].strip().lower()

    def _filename(self, media_id: str, content_type: str) -> str:
        safe_media_id = re.sub(r"[^a-zA-Z0-9_-]", "_", media_id)[:80] or "media"
        suffix = mimetypes.guess_extension(content_type) or ".img"
        return f"whatsapp_{safe_media_id}{suffix}"

    def _ensure_configured(self) -> None:
        if not self.access_token:
            raise AppException(
                message="WhatsApp media download is not configured.",
                status_code=500,
                error_code="whatsapp_media_download_failed",
            )

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    @asynccontextmanager
    async def _client_context(self) -> AsyncIterator[httpx.AsyncClient]:
        if self.http_client is not None:
            yield self.http_client
            return

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            yield client
