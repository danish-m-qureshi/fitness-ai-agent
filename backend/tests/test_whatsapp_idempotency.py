from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_whatsapp_service
from app.core.exceptions import AppException
from app.main import create_app
from app.models.user import User
from app.schemas.agent import AgentRequest, AgentResponse
from app.schemas.whatsapp import WhatsAppWebhookPayload, WhatsAppWebhookResponse
from app.services.user_service import UserService
from app.services.whatsapp.processed_message_service import (
    ProcessedWhatsAppMessageService,
)
from app.services.whatsapp.provider_base import WhatsAppProvider
from app.services.whatsapp.whatsapp_service import WhatsAppService


class RecordingWhatsAppProvider(WhatsAppProvider):
    name = "recording"

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
            response_text="Handled once.",
            user_id=request.user_id,
            meal_id=123,
        )


class FakeMediaDownloader:
    def __init__(self, image_path: Path) -> None:
        self.image_path = image_path
        self.calls = 0

    async def download_image(self, image_id: str):
        if not image_id:
            raise AppException(
                message="Missing media ID.",
                status_code=502,
                error_code="whatsapp_media_download_failed",
            )

        self.calls += 1
        return SimpleNamespace(
            stored_image=SimpleNamespace(path=str(self.image_path)),
        )


class IgnoredWhatsAppService:
    async def handle_webhook(
        self,
        payload: WhatsAppWebhookPayload,
    ) -> WhatsAppWebhookResponse:
        return WhatsAppWebhookResponse(
            status="ignored",
            provider="recording",
            intent="unknown",
            sender="15551234567",
        )


def create_user(db_session: Session) -> User:
    user = User(
        name="Idempotency User",
        email="idempotency@example.com",
        phone_number="+15551234567",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_service(
    db_session: Session,
    provider: RecordingWhatsAppProvider,
    agent: RecordingAgent,
    media_downloader: FakeMediaDownloader | None = None,
) -> WhatsAppService:
    return WhatsAppService(
        provider=provider,
        agent=agent,  # type: ignore[arg-type]
        user_service=UserService(db_session),
        media_downloader=media_downloader,  # type: ignore[arg-type]
        processed_message_service=ProcessedWhatsAppMessageService(db_session),
    )


def meta_text_payload(
    whatsapp_message_id: str,
    text: str = "I ate chicken rice",
) -> dict[str, Any]:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-id",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "id": whatsapp_message_id,
                                    "timestamp": "1790000000",
                                    "text": {"body": text},
                                    "type": "text",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def meta_image_payload(
    whatsapp_message_id: str,
    image_id: str = "media-123",
) -> dict[str, Any]:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-id",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "id": whatsapp_message_id,
                                    "timestamp": "1790000000",
                                    "image": {"id": image_id},
                                    "type": "image",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


@pytest.mark.asyncio
async def test_same_text_message_id_sent_twice_sends_only_one_reply(
    db_session: Session,
) -> None:
    create_user(db_session)
    provider = RecordingWhatsAppProvider()
    agent = RecordingAgent()
    service = create_service(db_session, provider, agent)
    payload = WhatsAppWebhookPayload.model_validate(
        meta_text_payload("wamid.duplicate-text")
    )

    first = await service.handle_webhook(payload)
    second = await service.handle_webhook(payload)

    assert first.status == "received"
    assert first.intent == "meal_text"
    assert second.status == "ignored"
    assert len(agent.requests) == 1
    assert provider.sent_texts == [("15551234567", "Handled once.")]


@pytest.mark.asyncio
async def test_same_image_message_id_sent_twice_sends_only_one_reply(
    db_session: Session,
    tmp_path: Path,
) -> None:
    create_user(db_session)
    image_path = tmp_path / "meal.webp"
    image_path.write_bytes(b"webp-bytes")
    provider = RecordingWhatsAppProvider()
    agent = RecordingAgent()
    media_downloader = FakeMediaDownloader(image_path)
    service = create_service(db_session, provider, agent, media_downloader)
    payload = WhatsAppWebhookPayload.model_validate(
        meta_image_payload("wamid.duplicate-image")
    )

    first = await service.handle_webhook(payload)
    second = await service.handle_webhook(payload)

    assert first.status == "received"
    assert first.intent == "meal_image"
    assert second.status == "ignored"
    assert len(agent.requests) == 1
    assert agent.requests[0].image_path == str(image_path)
    assert media_downloader.calls == 1
    assert provider.sent_texts == [("15551234567", "Handled once.")]


def test_duplicate_webhook_response_returns_http_200() -> None:
    app = create_app()
    app.dependency_overrides[get_whatsapp_service] = lambda: IgnoredWhatsAppService()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/webhooks/whatsapp",
                json=meta_text_payload("wamid.http-duplicate"),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_different_message_ids_from_same_user_are_processed_normally(
    db_session: Session,
) -> None:
    create_user(db_session)
    provider = RecordingWhatsAppProvider()
    agent = RecordingAgent()
    service = create_service(db_session, provider, agent)

    first = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(meta_text_payload("wamid.first"))
    )
    second = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(meta_text_payload("wamid.second"))
    )

    assert first.status == "received"
    assert second.status == "received"
    assert len(agent.requests) == 2
    assert provider.sent_texts == [
        ("15551234567", "Handled once."),
        ("15551234567", "Handled once."),
    ]
