from datetime import datetime
from typing import Literal

from app.schemas.confidence import ConfidenceLevel, normalize_confidence
from pydantic import BaseModel, ConfigDict, Field, field_validator


class NutritionFoodCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    aliases: str | None = None
    calories_per_100g: float = Field(..., ge=0)
    protein_g_per_100g: float = Field(default=0, ge=0)
    carbs_g_per_100g: float = Field(default=0, ge=0)
    fat_g_per_100g: float = Field(default=0, ge=0)
    default_serving_grams: float | None = Field(default=None, gt=0)
    default_serving_description: str | None = Field(default=None, max_length=100)


class NutritionFoodUpdate(BaseModel):
    name: str = Field(default=None, min_length=1, max_length=150)
    aliases: str | None = None
    calories_per_100g: float = Field(default=None, ge=0)
    protein_g_per_100g: float = Field(default=None, ge=0)
    carbs_g_per_100g: float = Field(default=None, ge=0)
    fat_g_per_100g: float = Field(default=None, ge=0)
    default_serving_grams: float | None = Field(default=None, gt=0)
    default_serving_description: str | None = Field(default=None, max_length=100)


class NutritionFoodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    aliases: str | None
    calories_per_100g: float
    protein_g_per_100g: float
    carbs_g_per_100g: float
    fat_g_per_100g: float
    default_serving_grams: float | None
    default_serving_description: str | None
    created_at: datetime
    updated_at: datetime


class DetectedFoodNutritionInput(BaseModel):
    name: str = Field(..., min_length=1)
    estimated_portion: str | None = None
    estimated_grams: float | None = Field(default=None, gt=0)
    confidence: ConfidenceLevel = "low"
    notes: str | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, value: object) -> ConfidenceLevel:
        return normalize_confidence(value)


class NutritionEstimateRequest(BaseModel):
    detected_foods: list[DetectedFoodNutritionInput] = Field(default_factory=list)


class NutritionItemEstimate(BaseModel):
    name: str
    matched_food_id: int | None = None
    matched_food_name: str | None = None
    estimated_portion: str | None = None
    estimated_grams: float | None = None
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    confidence: ConfidenceLevel = "low"
    notes: str | None = None


class NutritionEstimateResponse(BaseModel):
    items: list[NutritionItemEstimate] = Field(default_factory=list)
    total_calories: int | None = None
    total_protein_g: float | None = None
    total_carbs_g: float | None = None
    total_fat_g: float | None = None
    confidence: ConfidenceLevel = "low"
    needs_user_clarification: bool = True
    clarifying_questions: list[str] = Field(default_factory=list)


class MealNutritionApplyRequest(BaseModel):
    detected_foods: list[DetectedFoodNutritionInput] = Field(default_factory=list)


class MealFoodItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_id: int
    nutrition_food_id: int | None
    name: str
    estimated_portion: str | None
    estimated_grams: float | None
    calories: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    confidence: str
    notes: str | None
    created_at: datetime


class MealNutritionResponse(BaseModel):
    meal_id: int
    total_calories: int | None
    total_protein_g: float | None
    total_carbs_g: float | None
    total_fat_g: float | None
    confidence: Literal["low", "medium", "high"]
    items: list[MealFoodItemResponse] = Field(default_factory=list)
