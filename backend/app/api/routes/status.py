import logging
from datetime import datetime, timezone

from app.api.deps import get_db
from app.core.config import Settings, get_settings
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/status", tags=["status"])


class StatusResponse(BaseModel):
    app_name: str
    app_version: str
    environment: str
    debug: bool
    api_prefix: str
    database: str
    status: str
    timestamp_utc: datetime


@router.get("", response_model=StatusResponse)
def get_status(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> StatusResponse:
    database_status = "connected"

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database status check failed")
        database_status = "unavailable"

    return StatusResponse(
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug,
        api_prefix=settings.api_v1_prefix,
        database=database_status,
        status="running",
        timestamp_utc=datetime.now(timezone.utc),
    )
