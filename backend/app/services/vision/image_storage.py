import base64
import mimetypes
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core.exceptions import AppException
from starlette.datastructures import UploadFile

SAFE_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@dataclass(frozen=True)
class StoredImage:
    path: str
    content_type: str
    original_filename: str | None
    image_base64: str


class ImageStorageService:
    def __init__(self, upload_dir: str, max_image_bytes: int) -> None:
        self.upload_dir = Path(upload_dir)
        self.max_image_bytes = max_image_bytes

    async def save_meal_image(self, uploaded_image: UploadFile) -> StoredImage:
        content_type = uploaded_image.content_type or ""
        image_bytes = await uploaded_image.read()

        return self.save_meal_image_bytes(
            image_bytes=image_bytes,
            content_type=content_type,
            original_filename=uploaded_image.filename,
        )

    def save_meal_image_bytes(
        self,
        image_bytes: bytes,
        content_type: str,
        original_filename: str | None = None,
    ) -> StoredImage:
        content_type = self._normalized_content_type(content_type)
        self._validate_image_bytes(image_bytes=image_bytes, content_type=content_type)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        image_path = self.upload_dir / self._filename(
            original_filename=original_filename,
            content_type=content_type,
        )
        image_path.write_bytes(image_bytes)

        return StoredImage(
            path=str(image_path),
            content_type=content_type,
            original_filename=original_filename,
            image_base64=base64.b64encode(image_bytes).decode("utf-8"),
        )

    def _validate_image_bytes(self, image_bytes: bytes, content_type: str) -> None:
        if content_type not in SAFE_IMAGE_CONTENT_TYPES:
            raise AppException(
                message="Unsupported image type. Use JPEG, PNG, or WebP.",
                status_code=415,
                error_code="whatsapp_unsupported_media_type",
            )

        if not image_bytes:
            raise AppException(
                message="Uploaded image is empty.",
                status_code=400,
                error_code="empty_image_file",
            )

        if len(image_bytes) > self.max_image_bytes:
            raise AppException(
                message="Uploaded image is too large.",
                status_code=413,
                error_code="whatsapp_media_too_large",
            )

    def _normalized_content_type(self, content_type: str) -> str:
        return content_type.split(";", 1)[0].strip().lower()

    def _filename(self, original_filename: str | None, content_type: str) -> str:
        suffix = Path(original_filename or "").suffix.lower()
        if not suffix:
            suffix = mimetypes.guess_extension(content_type) or ".img"

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        return f"{timestamp}_{uuid.uuid4().hex}{suffix}"
