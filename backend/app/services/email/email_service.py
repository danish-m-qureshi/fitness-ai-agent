import html
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from app.core.config import Settings
from app.models.daily_summary import DailySummary
from app.models.user import User
from app.schemas.email import EmailDeliveryResult

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.template_path = Path(__file__).parent / "templates" / "daily_summary.html"

    def send_daily_summary(
        self,
        summary: DailySummary,
        user: User,
        to_email: str | None = None,
        dry_run: bool | None = None,
    ) -> EmailDeliveryResult:
        recipient = to_email or user.email
        subject = f"Daily fitness summary for {summary.summary_date.isoformat()}"

        if not recipient:
            return EmailDeliveryResult(
                status="skipped",
                recipient=None,
                subject=subject,
                reason="No recipient email is available for this user.",
            )

        should_dry_run = dry_run if dry_run is not None else self._is_dry_run()
        if should_dry_run:
            logger.info(
                "Daily summary email dry-run recipient=%s summary_id=%s",
                recipient,
                summary.id,
            )
            return EmailDeliveryResult(
                status="dry_run",
                recipient=recipient,
                subject=subject,
                reason="SMTP sending is disabled or not fully configured.",
            )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.settings.smtp_from_email or ""
        message["To"] = recipient
        message.set_content(self._plain_text(summary, user))
        message.add_alternative(self._html(summary, user), subtype="html")

        try:
            with smtplib.SMTP(
                self.settings.smtp_host,
                self.settings.smtp_port,
                timeout=15,
            ) as smtp:
                if self.settings.smtp_use_tls:
                    smtp.starttls()

                if self.settings.smtp_username:
                    smtp.login(
                        self.settings.smtp_username,
                        self.settings.smtp_password or "",
                    )

                smtp.send_message(message)
        except OSError as exc:
            logger.exception("Daily summary email failed")
            return EmailDeliveryResult(
                status="skipped",
                recipient=recipient,
                subject=subject,
                reason=f"SMTP send failed: {exc}",
            )

        logger.info(
            "Daily summary email sent recipient=%s summary_id=%s",
            recipient,
            summary.id,
        )
        return EmailDeliveryResult(
            status="sent",
            recipient=recipient,
            subject=subject,
        )

    def _is_dry_run(self) -> bool:
        return not (
            self.settings.summary_email_enabled
            and self.settings.smtp_host
            and self.settings.smtp_from_email
        )

    def _plain_text(self, summary: DailySummary, user: User) -> str:
        lines = [
            f"Hi {user.name},",
            "",
            summary.summary_text or "Your daily fitness summary is ready.",
            "",
            f"Calories: {summary.total_calories or 0}",
            f"Protein: {summary.total_protein_g or 0:g}g",
            f"Workouts: {summary.workouts_completed}",
            "",
            summary.coaching_suggestions or "",
        ]
        return "\n".join(lines).strip()

    def _html(self, summary: DailySummary, user: User) -> str:
        template = self.template_path.read_text(encoding="utf-8")
        replacements = {
            "name": html.escape(user.name),
            "summary_date": html.escape(summary.summary_date.isoformat()),
            "summary_text": html.escape(summary.summary_text or ""),
            "total_calories": str(summary.total_calories or 0),
            "calories_remaining": self._optional_int(summary.calories_remaining),
            "total_protein_g": self._optional_float(summary.total_protein_g),
            "workouts_completed": str(summary.workouts_completed),
            "latest_weight_kg": self._optional_float(summary.latest_weight_kg),
            "coaching_suggestions": html.escape(summary.coaching_suggestions or ""),
        }

        for key, value in replacements.items():
            template = template.replace("{{ " + key + " }}", value)

        return template

    def _optional_int(self, value: int | None) -> str:
        return "not set" if value is None else str(value)

    def _optional_float(self, value: float | None) -> str:
        return "not set" if value is None else f"{value:g}"
