from typing import Literal

from app.schemas.confidence import ConfidenceLevel, normalize_confidence
from app.schemas.nutrition import NutritionEstimateResponse
from pydantic import BaseModel, Field, field_validator


class DetectedFood(BaseModel):
    name: str = Field(..., min_length=1)
    estimated_portion: str = Field(..., min_length=1)
    confidence: ConfidenceLevel = "low"
    notes: str | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, value: object) -> ConfidenceLevel:
        return normalize_confidence(value)


class MealImageAnalysis(BaseModel):
    detected_foods: list[DetectedFood] = Field(default_factory=list)
    overall_confidence: ConfidenceLevel = "low"
    needs_user_clarification: bool = True
    clarifying_questions: list[str] = Field(default_factory=list)

    @field_validator("overall_confidence", mode="before")
    @classmethod
    def validate_overall_confidence(cls, value: object) -> ConfidenceLevel:
        return normalize_confidence(value)


class MealImageAnalysisResponse(BaseModel):
    success: bool
    model: str
    analysis: MealImageAnalysis | None = None
    nutrition_estimate: NutritionEstimateResponse | None = None
    raw_response: str | None = None
    error: str | None = None


class LLMHealthResponse(BaseModel):
    provider: str
    base_url: str
    model: str
    server_reachable: bool
    model_available: bool
    available_models: list[str] = Field(default_factory=list)
    status: Literal["ok", "unavailable", "model_missing"]
    error: str | None = None
