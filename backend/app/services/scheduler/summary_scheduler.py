import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.db.session import SessionLocal
from app.models.user import User
from app.services.daily_summary_service import DailySummaryService
from app.services.email.email_service import EmailService
from sqlalchemy import select

logger = logging.getLogger(__name__)


def start_summary_scheduler(settings: Settings) -> Any | None:
    if not settings.summary_schedule_enabled:
        logger.info("Daily summary scheduler disabled")
        return None

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning("APScheduler is not installed; scheduler not started")
        return None

    scheduler = BackgroundScheduler(timezone=settings.summary_schedule_timezone)
    scheduler.add_job(
        _send_scheduled_daily_summaries,
        trigger="cron",
        hour=settings.summary_schedule_hour,
        minute=settings.summary_schedule_minute,
        id="daily_summary_email",
        replace_existing=True,
        kwargs={"settings": settings},
    )
    scheduler.start()
    logger.info(
        "Daily summary scheduler started hour=%s minute=%s timezone=%s",
        settings.summary_schedule_hour,
        settings.summary_schedule_minute,
        settings.summary_schedule_timezone,
    )
    return scheduler


def shutdown_summary_scheduler(scheduler: Any | None) -> None:
    if scheduler is not None and getattr(scheduler, "running", False):
        scheduler.shutdown(wait=False)
        logger.info("Daily summary scheduler stopped")


def _send_scheduled_daily_summaries(settings: Settings) -> None:
    target_date = datetime.now(UTC).date()

    with SessionLocal() as db:
        users = list(
            db.scalars(
                select(User).where(User.email.is_not(None)).order_by(User.id)
            ).all()
        )
        summary_service = DailySummaryService(db)
        email_service = EmailService(settings)

        for user in users:
            summary = summary_service.generate_daily_summary(
                user_id=user.id,
                summary_date=target_date,
            )
            result = email_service.send_daily_summary(summary, user)
            if result.status == "sent":
                summary_service.mark_email_sent(summary.id)
