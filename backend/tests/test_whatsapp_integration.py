from pathlib import Path

import httpx
import pytest
from app.core.exceptions import AppException
from app.models.user import User
from app.schemas.agent import AgentRequest, AgentResponse
from app.schemas.whatsapp import WhatsAppWebhookPayload
from app.services.user_service import UserService
from app.services.vision.image_storage import ImageStorageService
from app.services.whatsapp.media_downloader import WhatsAppMediaDownloader
from app.services.whatsapp.provider_base import WhatsAppProvider
from app.services.whatsapp.whatsapp_service import WhatsAppService
from sqlalchemy.orm import Session


class FakeWhatsAppProvider(WhatsAppProvider):
    name = "fake"

    def __init__(self) -> None:
        self.sent_texts: list[tuple[str, str]] = []

    async def send_text(self, to: str, message: str) -> None:
        self.sent_texts.append((to, message))

    async def send_image(
        self,
        to: str,
        image_path: str,
        caption: str | None = None,
    ) -> None:
        pass


class RecordingAgent:
    def __init__(self) -> None:
        self.requests: list[AgentRequest] = []

    async def run(self, request: AgentRequest) -> AgentResponse:
        self.requests.append(request)
        return AgentResponse(
            status="completed",
            intent="meal_image" if request.image_path else "meal_text",
            response_text="Agent handled the WhatsApp message.",
            user_id=request.user_id,
            meal_id=123 if request.image_path or request.message_text else None,
        )


def create_user(
    db_session: Session,
    phone_number: str = "+15551234567",
) -> User:
    user = User(
        name="WhatsApp User",
        email="whatsapp-user@example.com",
        phone_number=phone_number,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_media_downloader(
    tmp_path: Path,
    handler: httpx.MockTransport,
    max_image_bytes: int = 1024,
) -> WhatsAppMediaDownloader:
    return WhatsAppMediaDownloader(
        access_token="test-token",
        api_base_url="https://graph.facebook.com",
        api_version="v20.0",
        image_storage_service=ImageStorageService(
            upload_dir=str(tmp_path),
            max_image_bytes=max_image_bytes,
        ),
        http_client=httpx.AsyncClient(transport=handler),
    )


def media_transport(
    image_bytes: bytes = b"image-bytes",
    metadata_mime_type: str = "image/jpeg",
    download_content_type: str = "image/jpeg",
    metadata_file_size: int | None = None,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-token"
        if str(request.url) == "https://graph.facebook.com/v20.0/media-123":
            payload = {
                "id": "media-123",
                "url": "https://media.example.test/download/media-123",
                "mime_type": metadata_mime_type,
            }
            if metadata_file_size is not None:
                payload["file_size"] = metadata_file_size
            return httpx.Response(200, json=payload)

        if str(request.url) == "https://media.example.test/download/media-123":
            return httpx.Response(
                200,
                headers={
                    "content-type": download_content_type,
                    "content-length": str(len(image_bytes)),
                },
                content=image_bytes,
            )

        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_phone_number_resolves_existing_user(db_session: Session) -> None:
    user = create_user(db_session, phone_number="+1 (555) 123-4567")
    provider = FakeWhatsAppProvider()
    agent = RecordingAgent()
    service = WhatsAppService(
        provider=provider,
        agent=agent,  # type: ignore[arg-type]
        user_service=UserService(db_session),
    )

    response = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(
            {
                "from": "15551234567",
                "type": "text",
                "text": "I ate chicken rice",
            }
        )
    )

    assert response.status == "received"
    assert response.error_code is None
    assert agent.requests[0].user_id == user.id
    assert provider.sent_texts == [
        ("15551234567", "Agent handled the WhatsApp message.")
    ]


@pytest.mark.asyncio
async def test_unknown_phone_returns_onboarding_response(
    db_session: Session,
) -> None:
    provider = FakeWhatsAppProvider()
    agent = RecordingAgent()
    service = WhatsAppService(
        provider=provider,
        agent=agent,  # type: ignore[arg-type]
        user_service=UserService(db_session),
    )

    response = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(
            {
                "from": "+15550000000",
                "type": "text",
                "text": "I ate chicken rice",
            }
        )
    )

    assert response.status == "received"
    assert response.intent == "unknown"
    assert response.error_code == "whatsapp_user_not_found"
    assert not agent.requests
    assert "do not recognize this phone number" in response.reply
    assert provider.sent_texts == [("+15550000000", response.reply)]


@pytest.mark.asyncio
async def test_local_user_id_shortcut_still_works(db_session: Session) -> None:
    provider = FakeWhatsAppProvider()
    agent = RecordingAgent()
    service = WhatsAppService(
        provider=provider,
        agent=agent,  # type: ignore[arg-type]
        user_service=UserService(db_session),
    )

    response = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(
            {
                "from": "+15550000000",
                "user_id": 77,
                "type": "text",
                "text": "I ate chicken rice",
            }
        )
    )

    assert response.status == "received"
    assert response.error_code is None
    assert agent.requests[0].user_id == 77


@pytest.mark.asyncio
async def test_media_downloader_happy_path_with_mocked_http(
    tmp_path: Path,
) -> None:
    downloader = create_media_downloader(
        tmp_path=tmp_path,
        handler=media_transport(image_bytes=b"jpeg-bytes"),
    )

    downloaded = await downloader.download_image("media-123")

    stored_path = Path(downloaded.stored_image.path)
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"jpeg-bytes"
    assert downloaded.stored_image.content_type == "image/jpeg"


@pytest.mark.asyncio
async def test_media_downloader_rejects_unsupported_mime_type(
    tmp_path: Path,
) -> None:
    downloader = create_media_downloader(
        tmp_path=tmp_path,
        handler=media_transport(metadata_mime_type="image/gif"),
    )

    with pytest.raises(AppException) as exc_info:
        await downloader.download_image("media-123")

    assert exc_info.value.error_code == "whatsapp_unsupported_media_type"


@pytest.mark.asyncio
async def test_media_downloader_rejects_oversized_media(tmp_path: Path) -> None:
    downloader = create_media_downloader(
        tmp_path=tmp_path,
        handler=media_transport(metadata_file_size=2048),
        max_image_bytes=1024,
    )

    with pytest.raises(AppException) as exc_info:
        await downloader.download_image("media-123")

    assert exc_info.value.error_code == "whatsapp_media_too_large"


@pytest.mark.asyncio
async def test_whatsapp_image_webhook_delegates_after_media_download(
    db_session: Session,
    tmp_path: Path,
) -> None:
    user = create_user(db_session)
    provider = FakeWhatsAppProvider()
    agent = RecordingAgent()
    downloader = create_media_downloader(
        tmp_path=tmp_path,
        handler=media_transport(
            image_bytes=b"webp-bytes",
            metadata_mime_type="image/webp",
            download_content_type="image/webp",
        ),
    )
    service = WhatsAppService(
        provider=provider,
        agent=agent,  # type: ignore[arg-type]
        user_service=UserService(db_session),
        media_downloader=downloader,
    )

    response = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(
            {
                "from": "15551234567",
                "type": "image",
                "image_id": "media-123",
            }
        )
    )

    assert response.status == "received"
    assert response.intent == "meal_image"
    assert response.meal_id == 123
    assert response.error_code is None
    assert agent.requests[0].user_id == user.id
    assert agent.requests[0].image_path is not None
    assert Path(agent.requests[0].image_path).exists()
    assert agent.requests[0].image_id is None
    assert provider.sent_texts == [
        ("15551234567", "Agent handled the WhatsApp message.")
    ]
