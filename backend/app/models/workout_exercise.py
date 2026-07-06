from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.db.base import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.exercise_catalog import ExerciseCatalog
    from app.models.exercise_set import ExerciseSet
    from app.models.workout_session import WorkoutSession


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_session_id: Mapped[int] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    exercise_catalog_id: Mapped[int | None] = mapped_column(
        ForeignKey("exercise_catalogs.id", ondelete="SET NULL"),
        index=True,
    )
    exercise_name: Mapped[str] = mapped_column(String(150), nullable=False)
    muscle_group: Mapped[str | None] = mapped_column(String(100))
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workout_session: Mapped["WorkoutSession"] = relationship(
        back_populates="exercises",
    )
    exercise_catalog: Mapped["ExerciseCatalog | None"] = relationship(
        back_populates="workout_exercises",
    )
    sets: Mapped[list["ExerciseSet"]] = relationship(
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
        order_by="ExerciseSet.set_number",
    )
