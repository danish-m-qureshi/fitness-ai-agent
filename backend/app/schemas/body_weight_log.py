from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BodyWeightLogCreate(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    weight_kg: float = Field(..., gt=0)
    notes: str | None = None
    logged_at: datetime | None = None


class BodyWeightLogUpdate(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    weight_kg: float = Field(default=None, gt=0)
    notes: str | None = None
    logged_at: datetime = None


class BodyWeightLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    weight_kg: float
    notes: str | None
    logged_at: datetime
    created_at: datetime
