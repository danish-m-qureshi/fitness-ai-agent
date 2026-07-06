from urllib.parse import urlparse

from app.api.deps import get_health_service
from app.core.config import Settings, get_settings
from app.core.exceptions import ResourceNotFoundError
from app.schemas.debug import DebugConfigResponse, DebugServicesResponse
from app.services.health_service import HealthService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/config", response_model=DebugConfigResponse)
def debug_config(
    settings: Settings = Depends(get_settings),
) -> DebugConfigResponse:
    _ensure_debug_enabled(settings)
    database = urlparse(settings.database_url)

    return DebugConfigResponse(
        environment=settings.environment,
        debug=settings.debug,
        api_prefix=settings.api_v1_prefix,
        api_key_enabled=settings.api_key_enabled,
        database={
            "scheme": database.scheme,
            "host": database.hostname,
            "port": database.port,
            "database": database.path.lstrip("/"),
        },
        qdrant={
            "host": settings.qdrant_host,
            "port": settings.qdrant_port,
            "collection": settings.qdrant_collection_name,
        },
        ollama={
            "base_url": settings.ollama_base_url,
            "vision_model": settings.vision_model,
            "embedding_model": settings.embedding_model_name,
        },
        email={
            "enabled": settings.summary_email_enabled,
            "smtp_host_configured": bool(settings.smtp_host),
            "from_email_configured": bool(settings.smtp_from_email),
        },
        scheduler={
            "enabled": settings.summary_schedule_enabled,
            "hour": settings.summary_schedule_hour,
            "minute": settings.summary_schedule_minute,
            "timezone": settings.summary_schedule_timezone,
        },
    )


@router.get("/services", response_model=DebugServicesResponse)
def debug_services(
    settings: Settings = Depends(get_settings),
    health_service: HealthService = Depends(get_health_service),
) -> DebugServicesResponse:
    _ensure_debug_enabled(settings)

    return DebugServicesResponse(
        services={
            "app": health_service.app().status,
            "redis": health_service.redis().status,
            "qdrant": health_service.qdrant().status,
            "ollama": health_service.ollama().status,
        }
    )


def _ensure_debug_enabled(settings: Settings) -> None:
    if settings.environment.lower() == "production" or not settings.debug:
        raise ResourceNotFoundError("Debug route")
