from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.db.base import Base
from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.body_weight_log import BodyWeightLog
    from app.models.daily_summary import DailySummary
    from app.models.goal import Goal
    from app.models.meal import Meal
    from app.models.workout import Workout
    from app.models.workout_session import WorkoutSession


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    phone_number: Mapped[str | None] = mapped_column(String(50), index=True)
    age: Mapped[int | None] = mapped_column(Integer)
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    goal_weight_kg: Mapped[float | None] = mapped_column(Float)
    activity_level: Mapped[str | None] = mapped_column(String(50))
    fitness_goal: Mapped[str | None] = mapped_column(String(100))
    daily_calorie_target: Mapped[int | None] = mapped_column(Integer)
    daily_protein_target_g: Mapped[float | None] = mapped_column(Float)
    timezone: Mapped[str] = mapped_column(
        String(80),
        default="UTC",
        server_default="UTC",
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

    meals: Mapped[list["Meal"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    workouts: Mapped[list["Workout"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    workout_sessions: Mapped[list["WorkoutSession"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    goals: Mapped[list["Goal"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    daily_summaries: Mapped[list["DailySummary"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    body_weight_logs: Mapped[list["BodyWeightLog"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
