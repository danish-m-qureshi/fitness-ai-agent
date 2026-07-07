import uuid
from datetime import datetime

from app.db.base import Base
from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class ProcessedWhatsAppMessage(Base):
    __tablename__ = "processed_whatsapp_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    whatsapp_message_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    sender_phone_number: Mapped[str | None] = mapped_column(String(50))
    message_type: Mapped[str | None] = mapped_column(String(50))
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
