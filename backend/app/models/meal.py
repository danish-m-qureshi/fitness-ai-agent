from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.db.base import Base
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.meal_food_item import MealFoodItem
    from app.models.user import User


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_calories: Mapped[int | None] = mapped_column(Integer)
    estimated_protein_g: Mapped[float | None] = mapped_column(Float)
    estimated_carbs_g: Mapped[float | None] = mapped_column(Float)
    estimated_fat_g: Mapped[float | None] = mapped_column(Float)
    nutrition_confidence: Mapped[str | None] = mapped_column(String(50))
    image_path: Mapped[str | None] = mapped_column(String(500))
    analysis_status: Mapped[str | None] = mapped_column(String(50))
    analysis_raw_response: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(
        String(50),
        default="text",
        nullable=False,
    )
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

    user: Mapped["User | None"] = relationship(back_populates="meals")
    food_items: Mapped[list["MealFoodItem"]] = relationship(
        back_populates="meal",
        cascade="all, delete-orphan",
    )
