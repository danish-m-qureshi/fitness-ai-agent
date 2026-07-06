from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from app.db.base import Base
from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.user import User


class DailySummary(Base):
    __tablename__ = "daily_summaries"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "summary_date",
            name="uq_daily_summaries_user_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    summary_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_calories: Mapped[int | None] = mapped_column(Integer)
    total_protein_g: Mapped[float | None] = mapped_column(Float)
    total_carbs_g: Mapped[float | None] = mapped_column(Float)
    total_fat_g: Mapped[float | None] = mapped_column(Float)
    calorie_target: Mapped[int | None] = mapped_column(Integer)
    calories_remaining: Mapped[int | None] = mapped_column(Integer)
    protein_target_g: Mapped[float | None] = mapped_column(Float)
    protein_remaining_g: Mapped[float | None] = mapped_column(Float)
    calories_burned: Mapped[int | None] = mapped_column(Integer)
    workouts_completed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    latest_weight_kg: Mapped[float | None] = mapped_column(Float)
    summary_text: Mapped[str | None] = mapped_column(Text)
    coaching_suggestions: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User | None"] = relationship(back_populates="daily_summaries")
