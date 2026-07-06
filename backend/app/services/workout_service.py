import logging
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from app.core.exceptions import AppException, ResourceNotFoundError
from app.models.exercise_set import ExerciseSet
from app.models.workout_exercise import WorkoutExercise
from app.models.workout_session import WorkoutSession
from app.schemas.workout import (
    ExerciseBestSet,
    ExerciseProgressResponse,
    ExerciseSetCreate,
    WeeklyVolumePoint,
    WorkoutCreate,
    WorkoutExerciseCreate,
    WorkoutUpdate,
)
from app.services.memory.memory_service import MemoryService
from app.services.user_helpers import ensure_user_exists
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

logger = logging.getLogger(__name__)


class WorkoutService:
    def __init__(
        self,
        db: Session,
        memory_service: MemoryService | None = None,
    ) -> None:
        self.db = db
        self.memory_service = memory_service

    def create_workout(self, workout_data: WorkoutCreate) -> WorkoutSession:
        ensure_user_exists(self.db, workout_data.user_id)

        workout = WorkoutSession(
            user_id=workout_data.user_id,
            started_at=workout_data.started_at or datetime.now(UTC),
            ended_at=workout_data.ended_at,
            notes=workout_data.notes,
        )

        for index, exercise_data in enumerate(workout_data.exercises):
            workout.exercises.append(
                self._build_exercise(
                    exercise_data=exercise_data,
                    fallback_order_index=index,
                )
            )

        self.db.add(workout)
        self.db.commit()
        self.db.refresh(workout)
        workout = self.get_workout(workout.id)
        self._remember_workout_session(workout)
        return workout

    def list_workouts(
        self,
        skip: int = 0,
        limit: int = 50,
        user_id: int | None = None,
    ) -> list[WorkoutSession]:
        statement = select(WorkoutSession).options(
            selectinload(WorkoutSession.exercises).selectinload(
                WorkoutExercise.sets,
            )
        )

        if user_id is not None:
            statement = statement.where(WorkoutSession.user_id == user_id)

        statement = (
            statement.order_by(WorkoutSession.started_at.desc().nullslast())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def get_workout(self, workout_id: int) -> WorkoutSession:
        statement = (
            select(WorkoutSession)
            .where(WorkoutSession.id == workout_id)
            .options(
                selectinload(WorkoutSession.exercises).selectinload(
                    WorkoutExercise.sets,
                )
            )
        )
        workout = self.db.scalars(statement).first()

        if workout is None:
            raise ResourceNotFoundError("Workout")

        return workout

    def update_workout(
        self,
        workout_id: int,
        workout_data: WorkoutUpdate,
    ) -> WorkoutSession:
        workout = self.get_workout(workout_id)
        updates = workout_data.model_dump(exclude_unset=True)

        if "user_id" in updates:
            ensure_user_exists(self.db, updates["user_id"])

        if (
            updates.get("started_at", workout.started_at)
            and updates.get("ended_at", workout.ended_at)
            and updates.get("ended_at", workout.ended_at)
            < updates.get("started_at", workout.started_at)
        ):
            raise AppException(
                message="Workout ended_at must be after started_at.",
                status_code=422,
                error_code="invalid_workout_time_range",
            )

        for field, value in updates.items():
            setattr(workout, field, value)

        self.db.commit()
        return self.get_workout(workout_id)

    def delete_workout(self, workout_id: int) -> None:
        workout = self.get_workout(workout_id)
        self.db.delete(workout)
        self.db.commit()

    def add_exercise(
        self,
        workout_id: int,
        exercise_data: WorkoutExerciseCreate,
    ) -> WorkoutExercise:
        workout = self.get_workout(workout_id)
        order_index = len(workout.exercises)
        exercise = self._build_exercise(
            exercise_data=exercise_data,
            fallback_order_index=order_index,
        )
        workout.exercises.append(exercise)
        self.db.commit()
        self.db.refresh(exercise)
        return exercise

    def add_set(
        self,
        workout_id: int,
        exercise_id: int,
        set_data: ExerciseSetCreate,
    ) -> ExerciseSet:
        exercise = self._get_workout_exercise(workout_id, exercise_id)
        exercise_set = ExerciseSet(**set_data.model_dump())
        exercise.sets.append(exercise_set)
        self.db.commit()
        self.db.refresh(exercise_set)
        return exercise_set

    def get_exercise_progress(
        self,
        exercise_name: str,
        user_id: int | None = None,
    ) -> ExerciseProgressResponse:
        normalized_name = exercise_name.strip().lower()
        statement = (
            select(ExerciseSet, WorkoutExercise, WorkoutSession)
            .join(
                WorkoutExercise,
                ExerciseSet.workout_exercise_id == WorkoutExercise.id,
            )
            .join(
                WorkoutSession,
                WorkoutExercise.workout_session_id == WorkoutSession.id,
            )
            .where(func.lower(WorkoutExercise.exercise_name) == normalized_name)
            .order_by(WorkoutSession.started_at.asc().nullslast())
        )

        if user_id is not None:
            statement = statement.where(WorkoutSession.user_id == user_id)

        rows = self.db.execute(statement).all()
        weekly_volume: dict[date, float] = defaultdict(float)
        sessions_seen: set[int] = set()
        best_set: ExerciseBestSet | None = None
        best_estimated_1rm: float | None = None
        total_volume = 0.0

        for exercise_set, workout_exercise, workout_session in rows:
            sessions_seen.add(workout_session.id)
            volume = self._set_volume(exercise_set)
            total_volume += volume

            performed_at = workout_session.started_at
            if performed_at is not None:
                week_start = self._week_start(performed_at)
                weekly_volume[week_start] += volume

            estimated_1rm = self._estimated_1rm(exercise_set)
            if estimated_1rm is not None and (
                best_estimated_1rm is None or estimated_1rm > best_estimated_1rm
            ):
                best_estimated_1rm = estimated_1rm
                best_set = ExerciseBestSet(
                    workout_session_id=workout_session.id,
                    workout_exercise_id=workout_exercise.id,
                    performed_at=performed_at,
                    set_number=exercise_set.set_number,
                    reps=exercise_set.reps,
                    weight_kg=exercise_set.weight_kg,
                    volume_kg=round(volume, 1),
                    estimated_1rm_kg=round(estimated_1rm, 1),
                )

        weekly_points = [
            WeeklyVolumePoint(
                week_start=week_start,
                total_volume_kg=round(volume, 1),
            )
            for week_start, volume in sorted(weekly_volume.items())
        ]

        return ExerciseProgressResponse(
            exercise_name=exercise_name.strip(),
            user_id=user_id,
            total_sessions=len(sessions_seen),
            total_sets=len(rows),
            total_volume_kg=round(total_volume, 1),
            best_estimated_1rm_kg=round(best_estimated_1rm, 1)
            if best_estimated_1rm is not None
            else None,
            best_set=best_set,
            weekly_volume=weekly_points,
            trend=self._trend(weekly_points),
        )

    def _build_exercise(
        self,
        exercise_data: WorkoutExerciseCreate,
        fallback_order_index: int,
    ) -> WorkoutExercise:
        exercise = WorkoutExercise(
            exercise_catalog_id=exercise_data.exercise_catalog_id,
            exercise_name=exercise_data.exercise_name.strip().lower(),
            muscle_group=exercise_data.muscle_group,
            order_index=exercise_data.order_index
            if exercise_data.order_index is not None
            else fallback_order_index,
            notes=exercise_data.notes,
        )

        for set_data in exercise_data.sets:
            exercise.sets.append(ExerciseSet(**set_data.model_dump()))

        return exercise

    def _get_workout_exercise(
        self,
        workout_id: int,
        exercise_id: int,
    ) -> WorkoutExercise:
        statement = select(WorkoutExercise).where(
            WorkoutExercise.id == exercise_id,
            WorkoutExercise.workout_session_id == workout_id,
        )
        exercise = self.db.scalars(statement).first()

        if exercise is None:
            raise ResourceNotFoundError("Workout exercise")

        return exercise

    def _remember_workout_session(self, workout: WorkoutSession) -> None:
        if self.memory_service is None or workout.user_id is None:
            return

        try:
            self.memory_service.remember_workout_session(workout)
        except Exception:
            logger.exception("Failed to store workout memory")

    def _set_volume(self, exercise_set: ExerciseSet) -> float:
        if exercise_set.weight_kg is None or exercise_set.reps is None:
            return 0.0

        return exercise_set.weight_kg * exercise_set.reps

    def _estimated_1rm(self, exercise_set: ExerciseSet) -> float | None:
        if exercise_set.weight_kg is None or exercise_set.reps is None:
            return None

        return exercise_set.weight_kg * (1 + exercise_set.reps / 30)

    def _week_start(self, value: datetime) -> date:
        local_date = value.date()
        return local_date - timedelta(days=local_date.weekday())

    def _trend(self, weekly_points: list[WeeklyVolumePoint]) -> str:
        if len(weekly_points) < 2:
            return "insufficient_data"

        previous = weekly_points[-2].total_volume_kg
        current = weekly_points[-1].total_volume_kg

        if current > previous:
            return "up"

        if current < previous:
            return "down"

        return "flat"
