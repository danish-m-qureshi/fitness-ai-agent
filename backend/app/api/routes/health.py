from app.api.deps import get_db, get_health_service
from app.schemas.health import HealthAggregateResponse, ServiceHealthResponse
from app.services.health_service import HealthService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthAggregateResponse)
def health_check(
    db: Session = Depends(get_db),
    health_service: HealthService = Depends(get_health_service),
) -> HealthAggregateResponse:
    return health_service.aggregate(db)


@router.get("/db", response_model=ServiceHealthResponse)
def health_db(
    db: Session = Depends(get_db),
    health_service: HealthService = Depends(get_health_service),
) -> ServiceHealthResponse:
    return health_service.db(db)


@router.get("/redis", response_model=ServiceHealthResponse)
def health_redis(
    health_service: HealthService = Depends(get_health_service),
) -> ServiceHealthResponse:
    return health_service.redis()


@router.get("/qdrant", response_model=ServiceHealthResponse)
def health_qdrant(
    health_service: HealthService = Depends(get_health_service),
) -> ServiceHealthResponse:
    return health_service.qdrant()


@router.get("/ollama", response_model=ServiceHealthResponse)
def health_ollama(
    health_service: HealthService = Depends(get_health_service),
) -> ServiceHealthResponse:
    return health_service.ollama()
