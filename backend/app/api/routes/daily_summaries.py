from datetime import date

from app.api.deps import get_daily_summary_service
from app.schemas.daily_summary import (
    DailySummaryCreate,
    DailySummaryResponse,
    DailySummaryUpdate,
)
from app.services.daily_summary_service import DailySummaryService
from fastapi import APIRouter, Depends, Query, Response, status

router = APIRouter(prefix="/daily-summaries", tags=["daily-summaries"])


@router.post(
    "",
    response_model=DailySummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_daily_summary(
    daily_summary: DailySummaryCreate,
    daily_summary_service: DailySummaryService = Depends(get_daily_summary_service),
) -> DailySummaryResponse:
    return daily_summary_service.create_daily_summary(daily_summary)


@router.get("", response_model=list[DailySummaryResponse])
def list_daily_summaries(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user_id: int | None = Query(default=None, ge=1),
    summary_date: date | None = None,
    daily_summary_service: DailySummaryService = Depends(get_daily_summary_service),
) -> list[DailySummaryResponse]:
    return daily_summary_service.list_daily_summaries(
        skip=skip,
        limit=limit,
        user_id=user_id,
        summary_date=summary_date,
    )


@router.get("/{summary_id}", response_model=DailySummaryResponse)
def get_daily_summary(
    summary_id: int,
    daily_summary_service: DailySummaryService = Depends(get_daily_summary_service),
) -> DailySummaryResponse:
    return daily_summary_service.get_daily_summary(summary_id)


@router.patch("/{summary_id}", response_model=DailySummaryResponse)
def update_daily_summary(
    summary_id: int,
    daily_summary: DailySummaryUpdate,
    daily_summary_service: DailySummaryService = Depends(get_daily_summary_service),
) -> DailySummaryResponse:
    return daily_summary_service.update_daily_summary(summary_id, daily_summary)


@router.delete("/{summary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_daily_summary(
    summary_id: int,
    daily_summary_service: DailySummaryService = Depends(get_daily_summary_service),
) -> Response:
    daily_summary_service.delete_daily_summary(summary_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
