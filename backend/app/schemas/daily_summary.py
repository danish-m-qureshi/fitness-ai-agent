from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DailySummaryCreate(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    summary_date: date
    total_calories: int | None = Field(default=None, ge=0)
    total_protein_g: float | None = Field(default=None, ge=0)
    total_carbs_g: float | None = Field(default=None, ge=0)
    total_fat_g: float | None = Field(default=None, ge=0)
    calorie_target: int | None = Field(default=None, ge=0)
    calories_remaining: int | None = None
    protein_target_g: float | None = Field(default=None, ge=0)
    protein_remaining_g: float | None = None
    calories_burned: int | None = Field(default=None, ge=0)
    workouts_completed: int = Field(default=0, ge=0)
    latest_weight_kg: float | None = Field(default=None, gt=0)
    summary_text: str | None = None
    coaching_suggestions: str | None = None
    notes: str | None = None
    email_sent_at: datetime | None = None


class DailySummaryUpdate(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    summary_date: date | None = None
    total_calories: int | None = Field(default=None, ge=0)
    total_protein_g: float | None = Field(default=None, ge=0)
    total_carbs_g: float | None = Field(default=None, ge=0)
    total_fat_g: float | None = Field(default=None, ge=0)
    calorie_target: int | None = Field(default=None, ge=0)
    calories_remaining: int | None = None
    protein_target_g: float | None = Field(default=None, ge=0)
    protein_remaining_g: float | None = None
    calories_burned: int | None = Field(default=None, ge=0)
    workouts_completed: int | None = Field(default=None, ge=0)
    latest_weight_kg: float | None = Field(default=None, gt=0)
    summary_text: str | None = None
    coaching_suggestions: str | None = None
    notes: str | None = None
    email_sent_at: datetime | None = None


class DailySummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    summary_date: date
    total_calories: int | None
    total_protein_g: float | None
    total_carbs_g: float | None
    total_fat_g: float | None
    calorie_target: int | None
    calories_remaining: int | None
    protein_target_g: float | None
    protein_remaining_g: float | None
    calories_burned: int | None
    workouts_completed: int
    latest_weight_kg: float | None
    summary_text: str | None
    coaching_suggestions: str | None
    notes: str | None
    email_sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DailySummarySendRequest(BaseModel):
    user_id: int = Field(..., ge=1)
    summary_date: date | None = None
    to_email: str | None = Field(default=None, max_length=255)
    dry_run: bool | None = None


class DailySummarySendResponse(BaseModel):
    status: Literal["sent", "dry_run", "skipped"]
    recipient: str | None = None
    subject: str
    reason: str | None = None
    summary: DailySummaryResponse
