import logging
from datetime import UTC, date, datetime, time, timedelta

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.models.body_weight_log import BodyWeightLog
from app.models.daily_summary import DailySummary
from app.models.goal import Goal
from app.models.meal import Meal
from app.models.user import User
from app.models.workout_session import WorkoutSession
from app.schemas.daily_summary import DailySummaryCreate, DailySummaryUpdate
from app.services.memory.memory_service import MemoryService
from app.services.user_helpers import ensure_user_exists
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DailySummaryService:
    def __init__(
        self,
        db: Session,
        memory_service: MemoryService | None = None,
    ) -> None:
        self.db = db
        self.memory_service = memory_service

    def create_daily_summary(
        self,
        summary_data: DailySummaryCreate,
    ) -> DailySummary:
        ensure_user_exists(self.db, summary_data.user_id)

        daily_summary = DailySummary(**summary_data.model_dump())
        self.db.add(daily_summary)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(
                message="Daily summary already exists for this user and date.",
                error_code="daily_summary_already_exists",
            ) from exc

        self.db.refresh(daily_summary)
        self._remember_daily_summary(daily_summary)
        return daily_summary

    def generate_daily_summary(
        self,
        user_id: int,
        summary_date: date | None = None,
    ) -> DailySummary:
        user = self.db.get(User, user_id)
        if user is None:
            raise ResourceNotFoundError("User")

        target_date = summary_date or datetime.now(UTC).date()
        start_at, end_at = self._day_bounds(target_date)
        meals = self._meals_for_day(user_id, start_at, end_at)
        workouts = self._workouts_for_day(user_id, start_at, end_at)
        latest_weight = self._latest_weight_for_day(user_id, start_at, end_at)
        active_goals = self._active_goal_titles(user_id)

        total_calories = self._sum_int(meal.estimated_calories for meal in meals)
        total_protein = self._sum_float(meal.estimated_protein_g for meal in meals)
        total_carbs = self._sum_float(meal.estimated_carbs_g for meal in meals)
        total_fat = self._sum_float(meal.estimated_fat_g for meal in meals)
        calories_remaining = (
            user.daily_calorie_target - total_calories
            if user.daily_calorie_target is not None
            else None
        )
        protein_remaining = (
            round(user.daily_protein_target_g - total_protein, 1)
            if user.daily_protein_target_g is not None
            else None
        )
        suggestions = self._coaching_suggestions(
            user=user,
            total_calories=total_calories,
            total_protein=total_protein,
            calories_remaining=calories_remaining,
            protein_remaining=protein_remaining,
            workouts_completed=len(workouts),
        )
        summary_text = self._summary_text(
            target_date=target_date,
            meals_count=len(meals),
            workouts_count=len(workouts),
            total_calories=total_calories,
            total_protein=total_protein,
            calories_remaining=calories_remaining,
            latest_weight=latest_weight,
            active_goals=active_goals,
        )

        payload = {
            "user_id": user_id,
            "summary_date": target_date,
            "total_calories": total_calories,
            "total_protein_g": round(total_protein, 1),
            "total_carbs_g": round(total_carbs, 1),
            "total_fat_g": round(total_fat, 1),
            "calorie_target": user.daily_calorie_target,
            "calories_remaining": calories_remaining,
            "protein_target_g": user.daily_protein_target_g,
            "protein_remaining_g": protein_remaining,
            "calories_burned": None,
            "workouts_completed": len(workouts),
            "latest_weight_kg": latest_weight.weight_kg if latest_weight else None,
            "summary_text": summary_text,
            "coaching_suggestions": suggestions,
            "notes": self._notes(meals, workouts),
        }

        daily_summary = self._upsert_daily_summary(
            user_id=user_id,
            summary_date=target_date,
            payload=payload,
        )
        self._remember_daily_summary(daily_summary)
        return daily_summary

    def list_daily_summaries(
        self,
        skip: int = 0,
        limit: int = 50,
        user_id: int | None = None,
        summary_date: date | None = None,
    ) -> list[DailySummary]:
        statement = select(DailySummary)

        if user_id is not None:
            statement = statement.where(DailySummary.user_id == user_id)

        if summary_date is not None:
            statement = statement.where(DailySummary.summary_date == summary_date)

        statement = (
            statement.order_by(DailySummary.summary_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def get_daily_summary(self, summary_id: int) -> DailySummary:
        daily_summary = self.db.get(DailySummary, summary_id)

        if daily_summary is None:
            raise ResourceNotFoundError("Daily summary")

        return daily_summary

    def update_daily_summary(
        self,
        summary_id: int,
        summary_data: DailySummaryUpdate,
    ) -> DailySummary:
        daily_summary = self.get_daily_summary(summary_id)
        updates = summary_data.model_dump(exclude_unset=True)

        if "user_id" in updates:
            ensure_user_exists(self.db, updates["user_id"])

        for field, value in updates.items():
            setattr(daily_summary, field, value)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(
                message="Daily summary already exists for this user and date.",
                error_code="daily_summary_already_exists",
            ) from exc

        self.db.refresh(daily_summary)
        self._remember_daily_summary(daily_summary)
        return daily_summary

    def mark_email_sent(self, summary_id: int) -> DailySummary:
        daily_summary = self.get_daily_summary(summary_id)
        daily_summary.email_sent_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(daily_summary)
        return daily_summary

    def delete_daily_summary(self, summary_id: int) -> None:
        daily_summary = self.get_daily_summary(summary_id)
        self.db.delete(daily_summary)
        self.db.commit()

    def _upsert_daily_summary(
        self,
        user_id: int,
        summary_date: date,
        payload: dict,
    ) -> DailySummary:
        statement = select(DailySummary).where(
            DailySummary.user_id == user_id,
            DailySummary.summary_date == summary_date,
        )
        daily_summary = self.db.scalars(statement).first()

        if daily_summary is None:
            daily_summary = DailySummary(**payload)
            self.db.add(daily_summary)
        else:
            for field, value in payload.items():
                setattr(daily_summary, field, value)

        self.db.commit()
        self.db.refresh(daily_summary)
        return daily_summary

    def _meals_for_day(
        self,
        user_id: int,
        start_at: datetime,
        end_at: datetime,
    ) -> list[Meal]:
        statement = (
            select(Meal)
            .where(
                Meal.user_id == user_id,
                Meal.created_at >= start_at,
                Meal.created_at < end_at,
            )
            .order_by(Meal.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def _workouts_for_day(
        self,
        user_id: int,
        start_at: datetime,
        end_at: datetime,
    ) -> list[WorkoutSession]:
        workout_time = func.coalesce(
            WorkoutSession.started_at, WorkoutSession.created_at
        )
        statement = (
            select(WorkoutSession)
            .where(
                WorkoutSession.user_id == user_id,
                workout_time >= start_at,
                workout_time < end_at,
            )
            .order_by(workout_time.asc())
        )
        return list(self.db.scalars(statement).all())

    def _latest_weight_for_day(
        self,
        user_id: int,
        start_at: datetime,
        end_at: datetime,
    ) -> BodyWeightLog | None:
        statement = (
            select(BodyWeightLog)
            .where(
                BodyWeightLog.user_id == user_id,
                BodyWeightLog.logged_at >= start_at,
                BodyWeightLog.logged_at < end_at,
            )
            .order_by(BodyWeightLog.logged_at.desc())
            .limit(1)
        )
        return self.db.scalars(statement).first()

    def _active_goal_titles(self, user_id: int) -> list[str]:
        statement = (
            select(Goal.title)
            .where(Goal.user_id == user_id, Goal.status == "active")
            .order_by(Goal.created_at.desc())
            .limit(5)
        )
        return list(self.db.scalars(statement).all())

    def _day_bounds(self, value: date) -> tuple[datetime, datetime]:
        start_at = datetime.combine(value, time.min, tzinfo=UTC)
        return start_at, start_at + timedelta(days=1)

    def _sum_int(self, values: object) -> int:
        return int(sum(value or 0 for value in values))

    def _sum_float(self, values: object) -> float:
        return float(sum(value or 0 for value in values))

    def _summary_text(
        self,
        target_date: date,
        meals_count: int,
        workouts_count: int,
        total_calories: int,
        total_protein: float,
        calories_remaining: int | None,
        latest_weight: BodyWeightLog | None,
        active_goals: list[str],
    ) -> str:
        parts = [
            f"Summary for {target_date.isoformat()}",
            f"{meals_count} meals logged",
            f"{total_calories} calories",
            f"{total_protein:g}g protein",
            f"{workouts_count} workouts completed",
        ]

        if calories_remaining is not None:
            parts.append(f"{calories_remaining} calories remaining")
        if latest_weight is not None:
            parts.append(f"latest weight {latest_weight.weight_kg:g}kg")
        if active_goals:
            parts.append(f"active goals: {', '.join(active_goals)}")

        return "; ".join(parts) + "."

    def _coaching_suggestions(
        self,
        user: User,
        total_calories: int,
        total_protein: float,
        calories_remaining: int | None,
        protein_remaining: float | None,
        workouts_completed: int,
    ) -> str:
        suggestions: list[str] = []

        if calories_remaining is not None:
            if calories_remaining > 500:
                suggestions.append("You have room for a balanced meal or snack.")
            elif calories_remaining < 0:
                suggestions.append(
                    "You are over the calorie target; keep the next meal lighter."
                )
            else:
                suggestions.append("You are close to the calorie target.")

        if protein_remaining is not None and protein_remaining > 0:
            suggestions.append(f"Prioritize about {protein_remaining:g}g more protein.")
        elif (
            user.daily_protein_target_g is not None
            and total_protein >= user.daily_protein_target_g
        ):
            suggestions.append("Protein target is on track.")

        if workouts_completed == 0:
            suggestions.append("No workout is logged yet today.")

        if not suggestions and total_calories == 0:
            suggestions.append("Start logging meals to build a useful daily summary.")

        return " ".join(suggestions)

    def _notes(self, meals: list[Meal], workouts: list[WorkoutSession]) -> str:
        meal_names = [meal.description for meal in meals[:5]]
        workout_notes = [workout.notes for workout in workouts if workout.notes]
        notes: list[str] = []

        if meal_names:
            notes.append(f"Meals: {', '.join(meal_names)}.")
        if workout_notes:
            notes.append(f"Workout notes: {' '.join(workout_notes[:3])}")

        return " ".join(notes) if notes else ""

    def _remember_daily_summary(self, summary: DailySummary) -> None:
        if self.memory_service is None or summary.user_id is None:
            return

        try:
            self.memory_service.remember_daily_summary(summary)
        except Exception:
            logger.exception("Failed to store daily summary memory")
