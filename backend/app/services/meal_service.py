import logging

from app.core.exceptions import MealDescriptionTooVagueError, ResourceNotFoundError
from app.models.meal import Meal
from app.models.meal_food_item import MealFoodItem
from app.schemas.meal import MealCreate, MealTextRequest, MealTextResponse, MealUpdate
from app.schemas.nutrition import NutritionEstimateResponse
from app.services.memory.memory_service import MemoryService
from app.services.user_helpers import ensure_user_exists
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MealService:
    def __init__(
        self,
        db: Session,
        memory_service: MemoryService | None = None,
    ) -> None:
        self.db = db
        self.memory_service = memory_service

    vague_terms = {
        "food",
        "meal",
        "something",
        "stuff",
        "things",
        "idk",
        "whatever",
    }

    def log_text_meal(self, meal: MealTextRequest) -> MealTextResponse:
        description = meal.description.strip()

        self._validate_description(description)

        meal_record = self._create_meal_record(
            description=description,
            estimated_calories=None,
            source="text",
        )

        logger.info("Persisted text meal description")

        return MealTextResponse(
            description=meal_record.description,
            estimated_calories=meal_record.estimated_calories,
            status="received",
        )

    def create_meal(self, meal_data: MealCreate) -> Meal:
        ensure_user_exists(self.db, meal_data.user_id)

        description = meal_data.description.strip()
        self._validate_description(description)

        return self._create_meal_record(
            user_id=meal_data.user_id,
            description=description,
            estimated_calories=meal_data.estimated_calories,
            source=meal_data.source,
        )

    def create_analyzed_image_meal(
        self,
        user_id: int,
        description: str,
        image_path: str,
        analysis_status: str,
        analysis_raw_response: str | None,
        confidence_score: float | None,
        nutrition_estimate: NutritionEstimateResponse,
    ) -> Meal:
        ensure_user_exists(self.db, user_id)

        meal = Meal(
            user_id=user_id,
            description=description.strip(),
            estimated_calories=nutrition_estimate.total_calories,
            estimated_protein_g=nutrition_estimate.total_protein_g,
            estimated_carbs_g=nutrition_estimate.total_carbs_g,
            estimated_fat_g=nutrition_estimate.total_fat_g,
            nutrition_confidence=nutrition_estimate.confidence,
            source="image",
            image_path=image_path,
            analysis_status=analysis_status,
            analysis_raw_response=analysis_raw_response,
            confidence_score=confidence_score,
        )

        for item in nutrition_estimate.items:
            meal.food_items.append(
                MealFoodItem(
                    nutrition_food_id=item.matched_food_id,
                    name=item.name,
                    estimated_portion=item.estimated_portion,
                    estimated_grams=item.estimated_grams,
                    calories=item.calories,
                    protein_g=item.protein_g,
                    carbs_g=item.carbs_g,
                    fat_g=item.fat_g,
                    confidence=item.confidence,
                    notes=item.notes,
                )
            )

        try:
            self.db.add(meal)
            self.db.commit()
            self.db.refresh(meal)
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception("Failed to persist analyzed image meal")
            raise

        self._remember_meal(meal)
        return meal

    def list_meals(
        self,
        skip: int = 0,
        limit: int = 50,
        user_id: int | None = None,
    ) -> list[Meal]:
        statement = select(Meal)

        if user_id is not None:
            statement = statement.where(Meal.user_id == user_id)

        statement = statement.order_by(Meal.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(statement).all())

    def get_meal(self, meal_id: int) -> Meal:
        meal = self.db.get(Meal, meal_id)

        if meal is None:
            raise ResourceNotFoundError("Meal")

        return meal

    def update_meal(self, meal_id: int, meal_data: MealUpdate) -> Meal:
        meal = self.get_meal(meal_id)
        updates = meal_data.model_dump(exclude_unset=True)

        if "user_id" in updates:
            ensure_user_exists(self.db, updates["user_id"])

        if "description" in updates and updates["description"] is not None:
            updates["description"] = updates["description"].strip()
            self._validate_description(updates["description"])

        for field, value in updates.items():
            setattr(meal, field, value)

        try:
            self.db.commit()
            self.db.refresh(meal)
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception("Failed to update meal")
            raise

        return meal

    def delete_meal(self, meal_id: int) -> None:
        meal = self.get_meal(meal_id)
        self.db.delete(meal)
        self.db.commit()

    def _create_meal_record(
        self,
        description: str,
        estimated_calories: int | None,
        source: str,
        user_id: int | None = None,
    ) -> Meal:
        meal_record = Meal(
            user_id=user_id,
            description=description,
            estimated_calories=estimated_calories,
            source=source,
        )

        try:
            self.db.add(meal_record)
            self.db.commit()
            self.db.refresh(meal_record)
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception("Failed to persist meal")
            raise

        self._remember_meal(meal_record)
        return meal_record

    def _validate_description(self, description: str) -> None:
        normalized_description = description.lower().strip()
        words = normalized_description.split()

        if normalized_description in self.vague_terms:
            raise MealDescriptionTooVagueError()

        if len(words) < 2:
            raise MealDescriptionTooVagueError()

        if all(word in self.vague_terms for word in words):
            raise MealDescriptionTooVagueError()

    def _remember_meal(self, meal: Meal) -> None:
        if self.memory_service is None or meal.user_id is None:
            return

        try:
            self.memory_service.remember_meal(meal)
        except Exception:
            logger.exception("Failed to store meal memory")
