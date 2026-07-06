import re

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.models.meal import Meal
from app.models.meal_food_item import MealFoodItem
from app.models.nutrition_food import NutritionFood
from app.schemas.confidence import ConfidenceLevel
from app.schemas.nutrition import (
    DetectedFoodNutritionInput,
    MealNutritionApplyRequest,
    MealNutritionResponse,
    NutritionEstimateRequest,
    NutritionEstimateResponse,
    NutritionFoodCreate,
    NutritionFoodUpdate,
    NutritionItemEstimate,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class NutritionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_food(self, food_data: NutritionFoodCreate) -> NutritionFood:
        food = NutritionFood(**food_data.model_dump())
        self.db.add(food)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(
                message="Nutrition food with this name already exists.",
                error_code="nutrition_food_already_exists",
            ) from exc

        self.db.refresh(food)
        return food

    def list_foods(
        self,
        skip: int = 0,
        limit: int = 100,
        query: str | None = None,
    ) -> list[NutritionFood]:
        statement = select(NutritionFood)

        if query:
            query_pattern = f"%{query.strip()}%"
            statement = statement.where(
                NutritionFood.name.ilike(query_pattern)
                | NutritionFood.aliases.ilike(query_pattern)
            )

        statement = statement.order_by(NutritionFood.name).offset(skip).limit(limit)
        return list(self.db.scalars(statement).all())

    def get_food(self, food_id: int) -> NutritionFood:
        food = self.db.get(NutritionFood, food_id)

        if food is None:
            raise ResourceNotFoundError("Nutrition food")

        return food

    def update_food(
        self,
        food_id: int,
        food_data: NutritionFoodUpdate,
    ) -> NutritionFood:
        food = self.get_food(food_id)
        updates = food_data.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(food, field, value)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(
                message="Nutrition food with this name already exists.",
                error_code="nutrition_food_already_exists",
            ) from exc

        self.db.refresh(food)
        return food

    def delete_food(self, food_id: int) -> None:
        food = self.get_food(food_id)
        self.db.delete(food)
        self.db.commit()

    def estimate_nutrition(
        self,
        request: NutritionEstimateRequest,
    ) -> NutritionEstimateResponse:
        return self._estimate_items(request.detected_foods)

    def apply_nutrition_to_meal(
        self,
        meal_id: int,
        request: MealNutritionApplyRequest,
    ) -> MealNutritionResponse:
        meal = self.db.get(Meal, meal_id)

        if meal is None:
            raise ResourceNotFoundError("Meal")

        estimate = self._estimate_items(request.detected_foods)

        meal.food_items.clear()

        for item in estimate.items:
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

        meal.estimated_calories = estimate.total_calories
        meal.estimated_protein_g = estimate.total_protein_g
        meal.estimated_carbs_g = estimate.total_carbs_g
        meal.estimated_fat_g = estimate.total_fat_g
        meal.nutrition_confidence = estimate.confidence

        self.db.commit()
        self.db.refresh(meal)

        return self.get_meal_nutrition(meal_id)

    def get_meal_nutrition(self, meal_id: int) -> MealNutritionResponse:
        meal = self.db.get(Meal, meal_id)

        if meal is None:
            raise ResourceNotFoundError("Meal")

        return MealNutritionResponse(
            meal_id=meal.id,
            total_calories=meal.estimated_calories,
            total_protein_g=meal.estimated_protein_g,
            total_carbs_g=meal.estimated_carbs_g,
            total_fat_g=meal.estimated_fat_g,
            confidence=meal.nutrition_confidence or "low",
            items=meal.food_items,
        )

    def _estimate_items(
        self,
        detected_foods: list[DetectedFoodNutritionInput],
    ) -> NutritionEstimateResponse:
        catalog = self._load_catalog()
        items: list[NutritionItemEstimate] = []
        clarifying_questions: list[str] = []

        for detected_food in detected_foods:
            matched_food = self._match_food(detected_food.name, catalog)
            item = self._estimate_single_item(detected_food, matched_food)
            items.append(item)

            if item.matched_food_id is None:
                clarifying_questions.append(
                    f"What is the closest common food for '{detected_food.name}'?"
                )
            elif item.estimated_grams is None:
                clarifying_questions.append(
                    f"How many grams or servings of {detected_food.name} did you eat?"
                )

        total_calories = self._sum_optional(item.calories for item in items)
        total_protein_g = self._round_optional(
            self._sum_optional(item.protein_g for item in items)
        )
        total_carbs_g = self._round_optional(
            self._sum_optional(item.carbs_g for item in items)
        )
        total_fat_g = self._round_optional(
            self._sum_optional(item.fat_g for item in items)
        )
        confidence = self._overall_confidence(items)

        return NutritionEstimateResponse(
            items=items,
            total_calories=round(total_calories)
            if total_calories is not None
            else None,
            total_protein_g=total_protein_g,
            total_carbs_g=total_carbs_g,
            total_fat_g=total_fat_g,
            confidence=confidence,
            needs_user_clarification=confidence != "high",
            clarifying_questions=clarifying_questions,
        )

    def _estimate_single_item(
        self,
        detected_food: DetectedFoodNutritionInput,
        matched_food: NutritionFood | None,
    ) -> NutritionItemEstimate:
        if matched_food is None:
            return NutritionItemEstimate(
                name=detected_food.name,
                estimated_portion=detected_food.estimated_portion,
                estimated_grams=detected_food.estimated_grams,
                confidence="low",
                notes=detected_food.notes or "No local nutrition match found.",
            )

        estimated_grams = self._estimate_grams(detected_food, matched_food)

        if estimated_grams is None:
            return NutritionItemEstimate(
                name=detected_food.name,
                matched_food_id=matched_food.id,
                matched_food_name=matched_food.name,
                estimated_portion=detected_food.estimated_portion,
                confidence="low",
                notes=detected_food.notes or "Portion size could not be estimated.",
            )

        multiplier = estimated_grams / 100
        calories = matched_food.calories_per_100g * multiplier
        protein_g = matched_food.protein_g_per_100g * multiplier
        carbs_g = matched_food.carbs_g_per_100g * multiplier
        fat_g = matched_food.fat_g_per_100g * multiplier

        return NutritionItemEstimate(
            name=detected_food.name,
            matched_food_id=matched_food.id,
            matched_food_name=matched_food.name,
            estimated_portion=detected_food.estimated_portion,
            estimated_grams=round(estimated_grams, 1),
            calories=round(calories, 1),
            protein_g=round(protein_g, 1),
            carbs_g=round(carbs_g, 1),
            fat_g=round(fat_g, 1),
            confidence=self._item_confidence(detected_food, matched_food),
            notes=detected_food.notes,
        )

    def _load_catalog(self) -> list[NutritionFood]:
        statement = select(NutritionFood).order_by(NutritionFood.name)
        return list(self.db.scalars(statement).all())

    def _match_food(
        self,
        food_name: str,
        catalog: list[NutritionFood],
    ) -> NutritionFood | None:
        normalized_name = self._normalize(food_name)
        best_match: NutritionFood | None = None
        best_score = 0

        for food in catalog:
            candidates = [food.name, *self._aliases(food.aliases)]

            for candidate in candidates:
                normalized_candidate = self._normalize(candidate)

                if normalized_name == normalized_candidate:
                    score = 300 + len(normalized_candidate)
                elif normalized_candidate in normalized_name:
                    score = 200 + len(normalized_candidate)
                elif normalized_name in normalized_candidate:
                    score = 100 + len(normalized_name)
                else:
                    score = 0

                if score > best_score:
                    best_score = score
                    best_match = food

        return best_match

    def _estimate_grams(
        self,
        detected_food: DetectedFoodNutritionInput,
        matched_food: NutritionFood,
    ) -> float | None:
        if detected_food.estimated_grams is not None:
            return detected_food.estimated_grams

        portion = (detected_food.estimated_portion or "").lower().strip()

        if not portion:
            return matched_food.default_serving_grams

        amount = self._extract_amount(portion)

        if re.search(r"\bkg\b|kilogram", portion):
            return amount * 1000

        if re.search(r"\bg\b|gram", portion):
            grams = self._extract_number_before_unit(portion, r"\bg\b|gram")
            return grams if grams is not None else amount

        if "cup" in portion:
            grams_per_cup = matched_food.default_serving_grams or 180
            return amount * grams_per_cup

        if "tablespoon" in portion or "tbsp" in portion:
            return amount * 15

        if "teaspoon" in portion or "tsp" in portion:
            return amount * 5

        if any(unit in portion for unit in ["piece", "slice", "serving"]):
            if matched_food.default_serving_grams is not None:
                return amount * matched_food.default_serving_grams

        if any(word in portion for word in ["small", "medium", "large"]):
            if matched_food.default_serving_grams is None:
                return None

            size_multiplier = 1.0
            if "small" in portion:
                size_multiplier = 0.75
            elif "large" in portion:
                size_multiplier = 1.25

            return amount * matched_food.default_serving_grams * size_multiplier

        if matched_food.default_serving_grams is not None:
            return amount * matched_food.default_serving_grams

        return None

    def _extract_amount(self, portion: str) -> float:
        match = re.search(r"(\d+(?:\.\d+)?|\d+/\d+)", portion)

        if match is None:
            return 1.0

        value = match.group(1)

        if "/" in value:
            numerator, denominator = value.split("/", 1)
            return float(numerator) / float(denominator)

        return float(value)

    def _extract_number_before_unit(
        self, portion: str, unit_pattern: str
    ) -> float | None:
        match = re.search(rf"(\d+(?:\.\d+)?)\s*(?:{unit_pattern})", portion)

        if match is None:
            return None

        return float(match.group(1))

    def _item_confidence(
        self,
        detected_food: DetectedFoodNutritionInput,
        matched_food: NutritionFood,
    ) -> ConfidenceLevel:
        if detected_food.estimated_grams is not None:
            return "high"

        if detected_food.estimated_portion and matched_food.default_serving_grams:
            return "medium"

        return "low"

    def _overall_confidence(
        self,
        items: list[NutritionItemEstimate],
    ) -> ConfidenceLevel:
        if not items:
            return "low"

        confidence_rank = {"low": 0, "medium": 1, "high": 2}
        lowest_rank = min(confidence_rank[item.confidence] for item in items)

        if lowest_rank == 2:
            return "high"

        if lowest_rank == 1:
            return "medium"

        return "low"

    def _sum_optional(self, values) -> float | None:
        present_values = [value for value in values if value is not None]

        if not present_values:
            return None

        return sum(present_values)

    def _round_optional(self, value: float | None) -> float | None:
        if value is None:
            return None

        return round(value, 1)

    def _normalize(self, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized[:-1] if normalized.endswith("s") else normalized

    def _aliases(self, aliases: str | None) -> list[str]:
        if not aliases:
            return []

        return [alias.strip() for alias in aliases.split(",") if alias.strip()]
