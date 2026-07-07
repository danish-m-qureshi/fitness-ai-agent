from collections.abc import Generator

from app.agents.fitness_agent import FitnessAgent
from app.core.config import Settings, get_settings
from app.core.exceptions import AppException
from app.db.session import SessionLocal
from app.services.body_weight_log_service import BodyWeightLogService
from app.services.daily_summary_service import DailySummaryService
from app.services.email.email_service import EmailService
from app.services.goal_service import GoalService
from app.services.health_service import HealthService
from app.services.llm.base import VisionLLMClient
from app.services.llm.ollama_client import OllamaVisionClient
from app.services.meal_service import MealService
from app.services.memory.embedding_service import EmbeddingService
from app.services.memory.memory_service import MemoryService
from app.services.memory.vector_store import QdrantVectorStore
from app.services.nutrition_service import NutritionService
from app.services.user_service import UserService
from app.services.vision.image_storage import ImageStorageService
from app.services.vision.meal_image_analyzer import MealImageAnalyzer
from app.services.whatsapp.provider_base import WhatsAppProvider
from app.services.whatsapp.media_downloader import WhatsAppMediaDownloader
from app.services.whatsapp.processed_message_service import (
    ProcessedWhatsAppMessageService,
)
from app.services.whatsapp.providers.meta_provider import MetaWhatsAppProvider
from app.services.whatsapp.providers.mock_provider import MockWhatsAppProvider
from app.services.whatsapp.whatsapp_service import WhatsAppService
from app.services.workout_service import WorkoutService
from fastapi import Depends
from sqlalchemy.orm import Session


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_embedding_service(
    settings: Settings = Depends(get_settings),
) -> EmbeddingService:
    return EmbeddingService(
        base_url=settings.ollama_base_url,
        model=settings.embedding_model_name,
        timeout_seconds=settings.ollama_timeout_seconds,
    )


def get_vector_store(
    settings: Settings = Depends(get_settings),
) -> QdrantVectorStore:
    return QdrantVectorStore(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection_name=settings.qdrant_collection_name,
    )


def get_memory_service(
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: QdrantVectorStore = Depends(get_vector_store),
) -> MemoryService:
    return MemoryService(
        embedding_service=embedding_service,
        vector_store=vector_store,
    )


def get_meal_service(
    db: Session = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MealService:
    return MealService(db, memory_service=memory_service)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_workout_service(
    db: Session = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> WorkoutService:
    return WorkoutService(db, memory_service=memory_service)


def get_whatsapp_provider(
    settings: Settings = Depends(get_settings),
) -> WhatsAppProvider:
    provider_name = settings.whatsapp_provider.lower().strip()

    if provider_name == "mock":
        return MockWhatsAppProvider()

    if provider_name == "meta":
        return MetaWhatsAppProvider(
            access_token=settings.whatsapp_meta_access_token,
            phone_number_id=settings.whatsapp_meta_phone_number_id,
            api_base_url=settings.whatsapp_meta_api_base_url,
            api_version=settings.whatsapp_meta_api_version,
        )

    raise AppException(
        message="Unsupported WhatsApp provider configured.",
        status_code=500,
        error_code="unsupported_whatsapp_provider",
    )


def get_goal_service(db: Session = Depends(get_db)) -> GoalService:
    return GoalService(db)


def get_daily_summary_service(
    db: Session = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> DailySummaryService:
    return DailySummaryService(db, memory_service=memory_service)


def get_email_service(
    settings: Settings = Depends(get_settings),
) -> EmailService:
    return EmailService(settings)


def get_health_service(
    settings: Settings = Depends(get_settings),
) -> HealthService:
    return HealthService(settings)


def get_body_weight_log_service(
    db: Session = Depends(get_db),
) -> BodyWeightLogService:
    return BodyWeightLogService(db)


def get_nutrition_service(db: Session = Depends(get_db)) -> NutritionService:
    return NutritionService(db)


def get_image_storage_service(
    settings: Settings = Depends(get_settings),
) -> ImageStorageService:
    return ImageStorageService(
        upload_dir=settings.meal_image_upload_dir,
        max_image_bytes=settings.max_image_upload_bytes,
    )


def get_whatsapp_media_downloader(
    image_storage_service: ImageStorageService = Depends(get_image_storage_service),
    settings: Settings = Depends(get_settings),
) -> WhatsAppMediaDownloader:
    return WhatsAppMediaDownloader(
        access_token=settings.whatsapp_meta_access_token,
        api_base_url=settings.whatsapp_meta_api_base_url,
        api_version=settings.whatsapp_meta_api_version,
        image_storage_service=image_storage_service,
    )


def get_processed_whatsapp_message_service(
    db: Session = Depends(get_db),
) -> ProcessedWhatsAppMessageService:
    return ProcessedWhatsAppMessageService(db)


def get_vision_llm_client(
    settings: Settings = Depends(get_settings),
) -> VisionLLMClient:
    if settings.llm_provider.lower() != "ollama":
        raise AppException(
            message="Unsupported LLM provider configured.",
            status_code=500,
            error_code="unsupported_llm_provider",
        )

    return OllamaVisionClient(
        base_url=settings.ollama_base_url,
        model=settings.vision_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )


def get_meal_image_analyzer(
    vision_client: VisionLLMClient = Depends(get_vision_llm_client),
    settings: Settings = Depends(get_settings),
) -> MealImageAnalyzer:
    return MealImageAnalyzer(
        vision_client=vision_client,
        model=settings.vision_model,
    )


def get_fitness_agent(
    meal_service: MealService = Depends(get_meal_service),
    workout_service: WorkoutService = Depends(get_workout_service),
    body_weight_log_service: BodyWeightLogService = Depends(
        get_body_weight_log_service
    ),
    daily_summary_service: DailySummaryService = Depends(get_daily_summary_service),
    memory_service: MemoryService = Depends(get_memory_service),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
    user_service: UserService = Depends(get_user_service),
    email_service: EmailService = Depends(get_email_service),
    meal_image_analyzer: MealImageAnalyzer = Depends(get_meal_image_analyzer),
) -> FitnessAgent:
    return FitnessAgent(
        meal_service=meal_service,
        workout_service=workout_service,
        body_weight_log_service=body_weight_log_service,
        daily_summary_service=daily_summary_service,
        memory_service=memory_service,
        nutrition_service=nutrition_service,
        user_service=user_service,
        email_service=email_service,
        meal_image_analyzer=meal_image_analyzer,
    )


def get_whatsapp_service(
    whatsapp_provider: WhatsAppProvider = Depends(get_whatsapp_provider),
    agent: FitnessAgent = Depends(get_fitness_agent),
    user_service: UserService = Depends(get_user_service),
    media_downloader: WhatsAppMediaDownloader = Depends(get_whatsapp_media_downloader),
    processed_message_service: ProcessedWhatsAppMessageService = Depends(
        get_processed_whatsapp_message_service
    ),
) -> WhatsAppService:
    return WhatsAppService(
        provider=whatsapp_provider,
        agent=agent,
        user_service=user_service,
        media_downloader=media_downloader,
        processed_message_service=processed_message_service,
    )
