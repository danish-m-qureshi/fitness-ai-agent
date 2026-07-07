import json
from typing import Any

import httpx
import pytest
from sqlalchemy.orm import Session

from app.agents.fitness_agent import FitnessAgent
from app.core.config import Settings
from app.core.exceptions import AppException
from app.models.body_weight_log import BodyWeightLog
from app.models.daily_summary import DailySummary
from app.models.meal import Meal
from app.models.user import User
from app.models.workout_session import WorkoutSession
from app.schemas.agent import AgentRequest
from app.schemas.whatsapp import WhatsAppWebhookPayload
from app.services.body_weight_log_service import BodyWeightLogService
from app.services.daily_summary_service import DailySummaryService
from app.services.email.email_service import EmailService
from app.services.meal_service import MealService
from app.services.memory.memory_service import MemoryService
from app.services.nutrition_service import NutritionService
from app.services.user_service import UserService
from app.services.whatsapp.provider_base import WhatsAppProvider
from app.services.whatsapp.providers.meta_provider import MetaWhatsAppProvider
from app.services.whatsapp.whatsapp_service import WhatsAppService
from app.services.workout_service import WorkoutService


class FakeEmbeddingService:
    def embed_text(self, text: str) -> list[float]:
        assert text
        return [0.1, 0.2, 0.3]


class FakeVectorStore:
    def __init__(self) -> None:
        self.points: dict[str, dict] = {}

    def upsert_memory(
        self,
        memory_id: str,
        vector: list[float],
        payload: dict,
    ) -> str:
        self.points[memory_id] = {"id": memory_id, "vector": vector, "payload": payload}
        return memory_id

    def search_memory(
        self,
        vector: list[float],
        limit: int,
        user_id: int,
        memory_type: str | None = None,
    ) -> list[dict]:
        results = []
        for point in self.points.values():
            payload = point["payload"]
            if payload["user_id"] != user_id:
                continue
            if memory_type is not None and payload["memory_type"] != memory_type:
                continue
            results.append(
                {
                    "id": point["id"],
                    "payload": payload,
                    "score": 1.0,
                }
            )

        return results[:limit]

    def delete_memory(self, memory_id: str) -> None:
        self.points.pop(memory_id, None)


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


class FailingMetaWhatsAppProvider(WhatsAppProvider):
    name = "meta"

    async def send_text(self, to: str, message: str) -> None:
        raise AppException(
            message="Meta WhatsApp send failed.",
            status_code=502,
            error_code="whatsapp_meta_send_failed",
        )

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

    async def run(self, request: AgentRequest):
        self.requests.append(request)
        raise AssertionError("Status callbacks should not be delegated to the agent.")


def create_user(
    db_session: Session,
    phone_number: str = "+1 (555) 123-4567",
) -> User:
    user = User(
        name="Phase 20 User",
        email="phase20@example.com",
        phone_number=phone_number,
        daily_calorie_target=2400,
        daily_protein_target_g=160,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_memory_service() -> MemoryService:
    return MemoryService(
        embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
        vector_store=FakeVectorStore(),  # type: ignore[arg-type]
    )


def create_agent(
    db_session: Session,
    memory_service: MemoryService,
) -> FitnessAgent:
    return FitnessAgent(
        meal_service=MealService(db_session, memory_service=memory_service),
        workout_service=WorkoutService(db_session, memory_service=memory_service),
        body_weight_log_service=BodyWeightLogService(db_session),
        daily_summary_service=DailySummaryService(
            db_session,
            memory_service=memory_service,
        ),
        memory_service=memory_service,
        nutrition_service=NutritionService(db_session),
        user_service=UserService(db_session),
        email_service=EmailService(Settings(summary_email_enabled=False)),
    )


def meta_text_payload(text: str, sender: str = "15551234567") -> dict[str, Any]:
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
                            "metadata": {
                                "display_phone_number": "15557654321",
                                "phone_number_id": "phone-number-id",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Phase 20 User"},
                                    "wa_id": sender,
                                }
                            ],
                            "messages": [
                                {
                                    "from": sender,
                                    "id": "wamid.test-message",
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


def meta_status_payload(recipient: str = "15551234567") -> dict[str, Any]:
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
                            "metadata": {
                                "display_phone_number": "15557654321",
                                "phone_number_id": "phone-number-id",
                            },
                            "statuses": [
                                {
                                    "id": "wamid.outbound-message",
                                    "status": "delivered",
                                    "timestamp": "1790000001",
                                    "recipient_id": recipient,
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def meta_dashboard_sample_message_payload() -> dict[str, Any]:
    return meta_text_payload(
        text="Hello, this is a Meta dashboard sample message.",
        sender="16505551111",
    )


@pytest.mark.asyncio
async def test_real_meta_text_messages_persist_agent_flows(
    db_session: Session,
) -> None:
    user = create_user(db_session)
    memory_service = create_memory_service()
    provider = RecordingWhatsAppProvider()
    service = WhatsAppService(
        provider=provider,
        agent=create_agent(db_session, memory_service),
        user_service=UserService(db_session),
    )

    meal = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(
            meta_text_payload("I ate chicken biryani for lunch")
        )
    )
    workout = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(
            meta_text_payload("Bench press 50kg 3 sets of 10")
        )
    )
    weight = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(
            meta_text_payload("My weight is 82.4kg today")
        )
    )
    summary = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(
            meta_text_payload("How am I doing today?")
        )
    )

    assert meal.intent == "meal_text"
    assert meal.meal_id is not None
    persisted_meal = db_session.get(Meal, meal.meal_id)
    assert persisted_meal is not None
    assert persisted_meal.user_id == user.id
    assert persisted_meal.source == "whatsapp"
    assert persisted_meal.description == "chicken biryani for lunch"

    assert workout.intent == "workout_log"
    assert workout.workout_id is not None
    persisted_workout = db_session.get(WorkoutSession, workout.workout_id)
    assert persisted_workout is not None
    assert persisted_workout.user_id == user.id
    assert persisted_workout.exercises[0].exercise_name == "bench press"

    assert weight.intent == "weight_log"
    assert weight.weight_log_id is not None
    persisted_weight = db_session.get(BodyWeightLog, weight.weight_log_id)
    assert persisted_weight is not None
    assert persisted_weight.user_id == user.id
    assert persisted_weight.weight_kg == 82.4

    assert summary.intent == "summary_request"
    assert summary.daily_summary_id is not None
    persisted_summary = db_session.get(DailySummary, summary.daily_summary_id)
    assert persisted_summary is not None
    assert persisted_summary.user_id == user.id
    assert persisted_summary.workouts_completed == 1
    assert persisted_summary.latest_weight_kg == 82.4

    assert len(provider.sent_texts) == 4
    assert all(to == "15551234567" for to, _ in provider.sent_texts)
    assert "Meal logged" in provider.sent_texts[0][1]
    assert "Workout logged" in provider.sent_texts[1][1]
    assert "Weight logged" in provider.sent_texts[2][1]
    assert "Today:" in provider.sent_texts[3][1]


@pytest.mark.asyncio
async def test_meta_dashboard_sample_payload_unknown_sender_returns_safe_response(
    db_session: Session,
) -> None:
    service = WhatsAppService(
        provider=FailingMetaWhatsAppProvider(),
        agent=create_agent(db_session, create_memory_service()),
        user_service=UserService(db_session),
    )

    response = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(meta_dashboard_sample_message_payload())
    )

    assert response.status == "received"
    assert response.intent == "unknown"
    assert response.sender == "16505551111"
    assert response.error_code == "whatsapp_user_not_found"
    assert "do not recognize this phone number" in response.reply


@pytest.mark.asyncio
async def test_unknown_meta_text_phone_returns_onboarding(
    db_session: Session,
) -> None:
    provider = RecordingWhatsAppProvider()
    service = WhatsAppService(
        provider=provider,
        agent=create_agent(db_session, create_memory_service()),
        user_service=UserService(db_session),
    )

    response = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(
            meta_text_payload("I ate chicken biryani for lunch", sender="15550000000")
        )
    )

    assert response.status == "received"
    assert response.intent == "unknown"
    assert response.error_code == "whatsapp_user_not_found"
    assert "do not recognize this phone number" in response.reply
    assert provider.sent_texts == [("15550000000", response.reply)]


@pytest.mark.asyncio
async def test_outbound_reply_failure_does_not_fail_known_user_webhook(
    db_session: Session,
) -> None:
    user = create_user(db_session, phone_number="+1 650 555 1111")
    service = WhatsAppService(
        provider=FailingMetaWhatsAppProvider(),
        agent=create_agent(db_session, create_memory_service()),
        user_service=UserService(db_session),
    )

    response = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(
            meta_text_payload(
                "I ate chicken biryani for lunch",
                sender="16505551111",
            )
        )
    )

    assert response.status == "received"
    assert response.intent == "meal_text"
    assert response.meal_id is not None
    assert response.error_code == "whatsapp_reply_send_failed"
    assert response.error == "WhatsApp reply could not be sent."

    persisted_meal = db_session.get(Meal, response.meal_id)
    assert persisted_meal is not None
    assert persisted_meal.user_id == user.id
    assert persisted_meal.description == "chicken biryani for lunch"


@pytest.mark.asyncio
async def test_meta_status_callback_is_ignored_without_agent_reply(
    db_session: Session,
) -> None:
    provider = RecordingWhatsAppProvider()
    agent = RecordingAgent()
    service = WhatsAppService(
        provider=provider,
        agent=agent,  # type: ignore[arg-type]
        user_service=UserService(db_session),
    )

    response = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(meta_status_payload())
    )

    assert response.status == "ignored"
    assert response.intent == "unknown"
    assert response.sender == "15551234567"
    assert not provider.sent_texts
    assert not agent.requests


@pytest.mark.asyncio
async def test_meta_provider_send_text_posts_to_graph_api() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.reply"}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = MetaWhatsAppProvider(
        access_token="test-access-token",
        phone_number_id="phone-number-id",
        api_base_url="https://graph.facebook.com",
        api_version="v20.0",
        http_client=client,
    )

    try:
        await provider.send_text("15551234567", "Meal logged.")
    finally:
        await client.aclose()

    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == (
        "https://graph.facebook.com/v20.0/phone-number-id/messages"
    )
    assert request.headers["authorization"] == "Bearer test-access-token"
    assert json.loads(request.content) == {
        "messaging_product": "whatsapp",
        "to": "15551234567",
        "type": "text",
        "text": {"body": "Meal logged."},
    }
