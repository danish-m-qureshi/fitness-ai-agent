from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.db.base import Base
from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.meal import Meal
    from app.models.nutrition_food import NutritionFood


class MealFoodItem(Base):
    __tablename__ = "meal_food_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    meal_id: Mapped[int] = mapped_column(
        ForeignKey("meals.id", ondelete="CASCADE"),
        index=True,
    )
    nutrition_food_id: Mapped[int | None] = mapped_column(
        ForeignKey("nutrition_foods.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    estimated_portion: Mapped[str | None] = mapped_column(String(150))
    estimated_grams: Mapped[float | None] = mapped_column(Float)
    calories: Mapped[float | None] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    carbs_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(50), default="low", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    meal: Mapped["Meal"] = relationship(back_populates="food_items")
    nutrition_food: Mapped["NutritionFood | None"] = relationship(
        back_populates="meal_items",
    )
