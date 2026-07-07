from datetime import UTC, datetime

from app.models.processed_whatsapp_message import ProcessedWhatsAppMessage
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class ProcessedWhatsAppMessageService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def reserve_message(
        self,
        whatsapp_message_id: str | None,
        sender_phone_number: str | None,
        message_type: str | None,
    ) -> bool:
        if not whatsapp_message_id:
            return True

        processed_message = ProcessedWhatsAppMessage(
            whatsapp_message_id=whatsapp_message_id,
            sender_phone_number=sender_phone_number,
            message_type=message_type,
            processed_at=datetime.now(UTC),
        )
        self.db.add(processed_message)

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return False

        return True
