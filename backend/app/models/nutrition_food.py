from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.db.base import Base
from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.meal_food_item import MealFoodItem


class NutritionFood(Base):
    __tablename__ = "nutrition_foods"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    aliases: Mapped[str | None] = mapped_column(Text)
    calories_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g_per_100g: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    carbs_g_per_100g: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    fat_g_per_100g: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    default_serving_grams: Mapped[float | None] = mapped_column(Float)
    default_serving_description: Mapped[str | None] = mapped_column(String(100))
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

    meal_items: Mapped[list["MealFoodItem"]] = relationship(
        back_populates="nutrition_food",
    )
