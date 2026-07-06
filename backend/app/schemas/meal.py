from datetime import datetime
from typing import Literal

from app.schemas.ai import MealImageAnalysis
from app.schemas.nutrition import NutritionEstimateResponse, NutritionItemEstimate
from pydantic import BaseModel, ConfigDict, Field


class MealTextRequest(BaseModel):
    description: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="Text description of the meal eaten by the user.",
        examples=["2 eggs, 1 paratha, 1 cup chai"],
    )


class MealTextResponse(BaseModel):
    description: str
    estimated_calories: int | None = None
    status: Literal["received"]


class MealCreate(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    description: str = Field(..., min_length=2, max_length=1000)
    estimated_calories: int | None = Field(default=None, ge=0)
    source: str = Field(default="manual", min_length=1, max_length=50)


class MealUpdate(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    description: str = Field(default=None, min_length=2, max_length=1000)
    estimated_calories: int | None = Field(default=None, ge=0)
    source: str = Field(default=None, min_length=1, max_length=50)


class MealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    description: str
    estimated_calories: int | None
    estimated_protein_g: float | None
    estimated_carbs_g: float | None
    estimated_fat_g: float | None
    nutrition_confidence: str | None
    image_path: str | None
    analysis_status: str | None
    confidence_score: float | None
    source: str
    created_at: datetime
    updated_at: datetime


class MealImageAnalysisSaveResponse(BaseModel):
    status: Literal["success", "model_missing", "model_not_ready", "error"]
    meal: MealResponse | None = None
    foods: list[NutritionItemEstimate] = Field(default_factory=list)
    total_calories: int | None = None
    total_protein_g: float | None = None
    total_carbs_g: float | None = None
    total_fat_g: float | None = None
    confidence: str | None = None
    notes: str | None = None
    disclaimer: str = (
        "This is an estimate, not a medical or dietitian-grade calculation."
    )
    analysis: MealImageAnalysis | None = None
    nutrition_estimate: NutritionEstimateResponse | None = None
    image_path: str | None = None
    error: str | None = None
