from datetime import date

from app.api.deps import get_daily_summary_service, get_email_service, get_user_service
from app.schemas.daily_summary import (
    DailySummaryResponse,
    DailySummarySendRequest,
    DailySummarySendResponse,
)
from app.services.daily_summary_service import DailySummaryService
from app.services.email.email_service import EmailService
from app.services.user_service import UserService
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.get("/daily", response_model=DailySummaryResponse)
def generate_daily_summary(
    user_id: int = Query(..., ge=1),
    summary_date: date | None = None,
    daily_summary_service: DailySummaryService = Depends(get_daily_summary_service),
) -> DailySummaryResponse:
    return daily_summary_service.generate_daily_summary(
        user_id=user_id,
        summary_date=summary_date,
    )


@router.post(
    "/daily/send",
    response_model=DailySummarySendResponse,
    status_code=status.HTTP_200_OK,
)
def send_daily_summary(
    request: DailySummarySendRequest,
    daily_summary_service: DailySummaryService = Depends(get_daily_summary_service),
    email_service: EmailService = Depends(get_email_service),
    user_service: UserService = Depends(get_user_service),
) -> DailySummarySendResponse:
    summary = daily_summary_service.generate_daily_summary(
        user_id=request.user_id,
        summary_date=request.summary_date,
    )
    user = user_service.get_user(request.user_id)
    result = email_service.send_daily_summary(
        summary=summary,
        user=user,
        to_email=request.to_email,
        dry_run=request.dry_run,
    )

    if result.status == "sent":
        summary = daily_summary_service.mark_email_sent(summary.id)

    return DailySummarySendResponse(
        status=result.status,
        recipient=result.recipient,
        subject=result.subject,
        reason=result.reason,
        summary=DailySummaryResponse.model_validate(summary),
    )
