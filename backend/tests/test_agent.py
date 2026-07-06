import pytest
from app.agents.fitness_agent import FitnessAgent
from app.core.config import Settings
from app.models.user import User
from app.schemas.agent import AgentRequest, AgentResponse
from app.schemas.ai import DetectedFood, MealImageAnalysis, MealImageAnalysisResponse
from app.schemas.nutrition import NutritionFoodCreate
from app.schemas.whatsapp import WhatsAppWebhookPayload
from app.services.body_weight_log_service import BodyWeightLogService
from app.services.daily_summary_service import DailySummaryService
from app.services.email.email_service import EmailService
from app.services.meal_service import MealService
from app.services.memory.memory_service import MemoryService
from app.services.nutrition_service import NutritionService
from app.services.user_service import UserService
from app.services.whatsapp.provider_base import WhatsAppProvider
from app.services.whatsapp.whatsapp_service import WhatsAppService
from app.services.workout_service import WorkoutService
from sqlalchemy.orm import Session


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


class FakeMealImageAnalyzer:
    async def analyze_image(self, image_base64: str) -> MealImageAnalysisResponse:
        assert image_base64
        return MealImageAnalysisResponse(
            success=True,
            model="fake-vision",
            analysis=MealImageAnalysis(
                detected_foods=[
                    DetectedFood(
                        name="chicken rice",
                        estimated_portion="1 bowl",
                        confidence="high",
                    )
                ],
                overall_confidence="high",
                needs_user_clarification=False,
            ),
            raw_response='{"detected_foods": ["chicken rice"]}',
        )


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


class FakeWhatsAppAgent:
    def __init__(self) -> None:
        self.requests: list[AgentRequest] = []

    async def run(self, request: AgentRequest) -> AgentResponse:
        self.requests.append(request)
        return AgentResponse(
            status="needs_input",
            intent="meal_image",
            response_text="Please download WhatsApp media before analysis.",
            user_id=request.user_id,
        )


def create_user(db_session: Session) -> User:
    user = User(
        name="Agent Test User",
        email="agent-test@example.com",
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
    meal_image_analyzer: FakeMealImageAnalyzer | None = None,
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
        meal_image_analyzer=meal_image_analyzer,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_fitness_agent_handles_core_intents_with_real_services(
    db_session: Session,
) -> None:
    user = create_user(db_session)
    memory_service = create_memory_service()
    agent = create_agent(db_session, memory_service)

    meal = await agent.run(
        AgentRequest(user_id=user.id, message_text="I ate chicken biryani for lunch")
    )
    assert meal.status == "completed"
    assert meal.intent == "meal_text"
    assert meal.meal_id is not None

    workout = await agent.run(
        AgentRequest(user_id=user.id, message_text="Bench press 50kg 3 sets of 10")
    )
    assert workout.status == "completed"
    assert workout.intent == "workout_log"
    assert workout.workout_id is not None

    weight = await agent.run(
        AgentRequest(user_id=user.id, message_text="My weight is 82.4kg today")
    )
    assert weight.status == "completed"
    assert weight.intent == "weight_log"
    assert weight.weight_log_id is not None

    summary = await agent.run(
        AgentRequest(user_id=user.id, message_text="How am I doing today?")
    )
    assert summary.status == "completed"
    assert summary.intent == "summary_request"
    assert summary.daily_summary_id is not None
    assert "Today:" in summary.response_text

    email = await agent.run(
        AgentRequest(user_id=user.id, message_text="Email me today's summary")
    )
    assert email.status == "completed"
    assert email.intent == "email_summary"
    assert email.daily_summary_id is not None
    assert email.tool_result["email_status"] == "dry_run"

    chat = await agent.run(
        AgentRequest(user_id=user.id, message_text="What can you help me with?")
    )
    assert chat.status == "completed"
    assert chat.intent == "general_chat"
    assert chat.memories
    assert "related note" in chat.response_text


@pytest.mark.asyncio
async def test_fitness_agent_handles_meal_images_and_missing_media(
    db_session: Session,
) -> None:
    user = create_user(db_session)
    memory_service = create_memory_service()
    nutrition_service = NutritionService(db_session)
    nutrition_service.create_food(
        NutritionFoodCreate(
            name="chicken rice",
            aliases="rice bowl",
            calories_per_100g=170,
            protein_g_per_100g=11,
            carbs_g_per_100g=19,
            fat_g_per_100g=5,
            default_serving_grams=350,
            default_serving_description="1 bowl",
        )
    )
    agent = create_agent(
        db_session,
        memory_service,
        meal_image_analyzer=FakeMealImageAnalyzer(),
    )

    image = await agent.run(
        AgentRequest(user_id=user.id, image_base64="ZmFrZS1pbWFnZQ==")
    )
    assert image.status == "completed"
    assert image.intent == "meal_image"
    assert image.meal_id is not None
    assert image.tool_result["estimated_calories"] == 595

    missing_media = await agent.run(AgentRequest(user_id=user.id, image_id="abc123"))
    assert missing_media.status == "needs_input"
    assert missing_media.intent == "meal_image"
    assert "downloaded before local analysis" in missing_media.response_text


@pytest.mark.asyncio
async def test_whatsapp_service_keeps_local_user_id_shortcut(
    db_session: Session,
) -> None:
    provider = FakeWhatsAppProvider()
    agent = FakeWhatsAppAgent()
    service = WhatsAppService(
        provider=provider,
        agent=agent,  # type: ignore[arg-type]
        user_service=UserService(db_session),
    )

    response = await service.handle_webhook(
        WhatsAppWebhookPayload.model_validate(
            {
                "from": "+15551234567",
                "user_id": 1,
                "type": "text",
                "text": "How am I doing today?",
            }
        )
    )

    assert response.status == "received"
    assert response.intent == "meal_image"
    assert response.reply == "Please download WhatsApp media before analysis."
    assert provider.sent_texts == [
        ("+15551234567", "Please download WhatsApp media before analysis.")
    ]
    assert agent.requests[0].user_id == 1
